#!/usr/bin/env python3
"""
PI2PRINTER Email Monitor Service
Continuously monitors Gmail for new emails and processes them into actionable tasks
"""

import os
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# Local imports
from database import Database
from printer_service import PrinterService
from utils import (
    setup_gmail_service, UnifiedLLMModel, 
    parse_gmail_message, create_task_analysis_prompt, clean_json_response
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmailMonitor:
    def __init__(self, check_interval_minutes: int = 5):
        """Initialize email monitor"""
        self.check_interval = check_interval_minutes * 60  # Convert to seconds
        self.db = Database()
        
        # Use Pi-specific printer configuration
        from pi_config import get_printer_config
        printer_config = get_printer_config()
        
        self.printer = PrinterService(
            bluetooth_addr=printer_config['bluetooth_addr'],
            serial_port=printer_config['serial_port'],
            network_host=printer_config['network_host'],
            fallback_to_file=printer_config['fallback_to_file']
        )
        
        # Setup APIs
        self.gmail_service = None
        self.llm_model = None
        
        self._setup_apis()
        
        # Store last check time
        last_check = self.db.get_config('last_email_check')
        if last_check:
            self.last_check = datetime.fromisoformat(last_check)
        else:
            # Default to 24 hours ago for first run
            self.last_check = datetime.now(timezone.utc) - timedelta(hours=24)
            
        logger.info(f"Email monitor initialized. Check interval: {check_interval_minutes} minutes")
        logger.info(f"Last check time: {self.last_check}")
    
    def _setup_apis(self):
        """Setup Gmail and Gemini APIs"""
        logger.info("Setting up APIs...")
        
        try:
            self.gmail_service = setup_gmail_service()
            self.llm_model = UnifiedLLMModel()
            logger.info("✅ APIs configured successfully")
        except Exception as e:
            logger.error(f"Failed to setup APIs: {e}")
            raise
    
    def fetch_new_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch new emails since last check"""
        logger.info(f"Checking for new emails since {self.last_check}")
        
        try:
            # Build query for recent emails
            # Gmail query format: after:YYYY/MM/DD
            query_date = self.last_check.strftime('%Y/%m/%d')
            query = f'in:inbox after:{query_date}'
            
            logger.info(f"Gmail query: {query}")
            
            # Get messages
            results = self.gmail_service.users().messages().list(
                userId='me',
                maxResults=limit,
                q=query
            ).execute()
            
            message_ids = results.get('messages', [])
            logger.info(f"Found {len(message_ids)} potential new messages")
            
            new_emails = []
            
            for msg_data in message_ids:
                message_id = msg_data['id']
                
                # Skip if already processed
                if self.db.is_email_processed(message_id):
                    logger.debug(f"Skipping already processed email: {message_id}")
                    continue
                
                # Get full message
                try:
                    message = self.gmail_service.users().messages().get(
                        userId='me', 
                        id=message_id
                    ).execute()
                    
                    email_data = parse_gmail_message(message)
                    if email_data:
                        new_emails.append(email_data)
                        logger.info(f"New email: {email_data['subject'][:50]}...")
                    
                except Exception as e:
                    logger.error(f"Failed to fetch message {message_id}: {e}")
                    continue
            
            logger.info(f"Found {len(new_emails)} new emails to process")
            return new_emails
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching emails: {e}")
            return []
    
    
    def analyze_email_for_tasks(self, email_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze email with Gemini to extract actionable tasks"""
        logger.info(f"Analyzing email with Gemini: {email_data['subject'][:50]}...")
        
        try:
            # Create standardized prompt for task extraction
            prompt = create_task_analysis_prompt(email_data)
            
            response = self.llm_model.generate_content(prompt)
            analysis_text = response.text.strip()
            
            # Remove any markdown formatting
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text[7:]
            if analysis_text.endswith('```'):
                analysis_text = analysis_text[:-3]
            
            analysis_text = analysis_text.strip()
            # Clean JSON response (remove comments, trailing commas, etc.)
            analysis_text = clean_json_response(analysis_text)
            
            # Parse JSON response
            try:
                analysis = json.loads(analysis_text)
                
                # Log analysis result
                has_task = analysis.get('has_task', False)
                confidence = analysis.get('confidence', 0.0)
                reasoning = analysis.get('reasoning', 'No reasoning provided')
                
                logger.info(f"Analysis result: has_task={has_task}, confidence={confidence:.2f}")
                logger.info(f"Reasoning: {reasoning}")
                
                return analysis
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                logger.error(f"Raw response: {analysis_text}")
                return None
                
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return None
    def _print_mission_with_retry(self, analysis, mission_id, max_retries=3, delay=2):
        """Print mission with automatic retry for Bluetooth busy errors"""
        import time
        
        for attempt in range(max_retries):
            try:
                success = self.printer.print_mission(analysis, "Agent Roshin")
                if success:
                    return True
                    
                # If print failed for non-busy reason, dont retry
                logger.warning(f"Print attempt {attempt + 1} failed for mission {mission_id}")
                
            except Exception as e:
                error_msg = str(e).lower()
                if "device or resource busy" in error_msg or "errno 16" in error_msg:
                    if attempt < max_retries - 1:  # Not the last attempt
                        logger.info(f"Bluetooth busy (attempt {attempt + 1}), waiting {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Bluetooth still busy after {max_retries} attempts")
                        return False
                else:
                    # Non-busy error, dont retry
                    logger.error(f"Print error for mission {mission_id}: {e}")
                    return False
                    
        return False

    
    def process_email(self, email_data: Dict[str, Any]) -> bool:
        """Process a single email: analyze and create task if needed"""
        logger.info(f"Processing email: {email_data['subject']}")
        
        try:
            # Analyze email for tasks
            analysis = self.analyze_email_for_tasks(email_data)
            
            if not analysis:
                logger.error("Failed to analyze email")
                self.db.mark_email_processed(email_data, has_task=False)
                return False
            
            # Check type of email (MISSION or MESSAGE or IGNORE)
            email_type = analysis.get('type', 'IGNORE')
            has_task = analysis.get('has_task', False)
            
            # Handle Mission (Task)
            if email_type == 'MISSION' or has_task:
                # Create mission in database
                mission_id = self.db.create_mission(analysis, email_data)
                
                if mission_id:
                    # Print mission briefing with retry for Bluetooth busy errors
                    success = self._print_mission_with_retry(analysis, mission_id)
                    
                    if success:
                        logger.info(f"✅ Mission printed: {mission_id}")
                    else:
                        logger.warning(f"⚠️ Print failed after retries: {mission_id}")
                    
                    # Mark email as processed with task
                    self.db.mark_email_processed(email_data, has_task=True, mission_id=mission_id)
                    return True
                else:
                    logger.error("Failed to create mission in database")
            
            # Handle Personal Message (Receipt)
            elif email_type == 'MESSAGE':
                logger.info(f"Found personal message, printing receipt...")
                receipt_data = analysis.get('receipt_data', {})
                if not receipt_data:
                     # Fallback if receipt data missing
                     receipt_data = {
                         'store_name': 'MESSAGE FROM ' + email_data.get('from', 'FRIEND')[:20],
                         'items': [{'name': 'Message content', 'price': '0.00'}],
                         'total': 'PRICELESS'
                     }
                
                # Print receipt (retry logic might be needed here too, but simple print for now)
                try:
                    success = self.printer.print_receipt(receipt_data)
                    if success:
                        logger.info(f"✅ Receipt printed for: {email_data['subject']}")
                    else:
                        logger.warning(f"⚠️ Receipt print failed")
                except Exception as e:
                    logger.error(f"Error printing receipt: {e}")
                
                # Mark as processed (no task)
                self.db.mark_email_processed(email_data, has_task=False)
                return True
            
            else:
                logger.info(f"No actionable task or message found in email")
            
            # Mark email as processed
            self.db.mark_email_processed(email_data, has_task=False)
            return True
            
        except Exception as e:
            logger.error(f"Failed to process email: {e}")
            # Still mark as processed to avoid reprocessing
            self.db.mark_email_processed(email_data, has_task=False)
            return False
    
    def run_check_cycle(self):
        """Run a single check cycle"""
        logger.info("Starting email check cycle...")
        
        try:
            # Fetch new emails
            new_emails = self.fetch_new_emails(limit=20)
            
            if not new_emails:
                logger.info("No new emails to process")
                return
            
            # Process each email
            processed_count = 0
            task_count = 0
            
            for email_data in new_emails:
                try:
                    if self.process_email(email_data):
                        processed_count += 1
                        
                        # Check if task was created (by checking if mission was created)
                        if not self.db.is_email_processed(email_data['id']):
                            continue
                        
                        # Quick check if this email resulted in a task
                        with self.db.get_connection() as conn:
                            cursor = conn.execute(
                                "SELECT has_task FROM processed_emails WHERE email_id = ?",
                                (email_data['id'],)
                            )
                            row = cursor.fetchone()
                            if row and row[0]:
                                task_count += 1
                    
                    # Small delay between emails to avoid rate limits
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing email {email_data['id']}: {e}")
                    continue
            
            # Update last check time
            self.last_check = datetime.now(timezone.utc)
            self.db.set_config('last_email_check', self.last_check.isoformat())
            
            logger.info(f"Check cycle complete: {processed_count} emails processed, {task_count} tasks created")
            
        except Exception as e:
            logger.error(f"Check cycle failed: {e}")
    
    def start_monitoring(self):
        """Start continuous email monitoring"""
        logger.info("🚀 Starting continuous email monitoring...")
        logger.info(f"Check interval: {self.check_interval/60:.1f} minutes")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                self.run_check_cycle()
                
                logger.info(f"Sleeping for {self.check_interval/60:.1f} minutes...")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring failed: {e}")
            raise
        finally:
            self.printer.close()
    
    def get_status(self) -> Dict[str, Any]:
        """Get monitoring status and stats"""
        stats = self.db.get_stats()
        
        return {
            'last_check': self.last_check.isoformat(),
            'check_interval_minutes': self.check_interval / 60,
            'printer_status': self.printer.get_printer_info(),
            'database_stats': stats
        }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='PI2PRINTER Email Monitor')
    parser.add_argument('--interval', '-i', type=int, default=5,
                      help='Check interval in minutes (default: 5)')
    parser.add_argument('--check-once', action='store_true',
                      help='Run one check cycle and exit')
    parser.add_argument('--status', action='store_true',
                      help='Show status and exit')
    
    args = parser.parse_args()
    
    try:
        monitor = EmailMonitor(check_interval_minutes=args.interval)
        
        if args.status:
            status = monitor.get_status()
            print(json.dumps(status, indent=2))
            return
        
        if args.check_once:
            monitor.run_check_cycle()
            return
        
        # Start continuous monitoring
        monitor.start_monitoring()
        
    except Exception as e:
        logger.error(f"Failed to start email monitor: {e}")
        raise


if __name__ == '__main__':
    main()
