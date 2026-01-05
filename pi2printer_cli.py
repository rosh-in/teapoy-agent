#!/usr/bin/env python3
"""
PI2PRINTER Command Line Interface
Manage email monitoring, view missions, and control the system
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Any

from database import Database
from email_monitor import EmailMonitor
from printer_service import PrinterService


class Pi2PrinterCLI:
    def __init__(self):
        self.db = Database()
    
    def status(self):
        """Show system status"""
        print("🎯 PI2PRINTER SYSTEM STATUS")
        print("=" * 50)
        
        try:
            monitor = EmailMonitor(check_interval_minutes=5)
            status_data = monitor.get_status()
            
            print(f"📧 Last Email Check: {status_data['last_check']}")
            print(f"⏱️  Check Interval: {status_data['check_interval_minutes']} minutes")
            print(f"🖨️  Printer: {status_data['printer_status']}")
            print()
            
            stats = status_data['database_stats']
            print("📊 STATISTICS:")
            
            if stats['missions_by_status']:
                print("   Missions by Status:")
                for status, count in stats['missions_by_status'].items():
                    print(f"     {status}: {count}")
            
            if stats['missions_by_urgency']:
                print("   Missions by Urgency:")
                for urgency, count in stats['missions_by_urgency'].items():
                    print(f"     {urgency}: {count}")
            
            print(f"   📨 Total emails processed: {stats['total_emails_processed']}")
            print(f"   ✅ Emails with tasks: {stats['emails_with_tasks']}")
            print(f"   🚀 Missions last 24h: {stats['missions_last_24h']}")
            
        except Exception as e:
            print(f"❌ Error getting status: {e}")
    
    def list_missions(self, status: str = None, limit: int = 10):
        """List recent missions"""
        print(f"🎯 RECENT MISSIONS (limit: {limit})")
        print("=" * 70)
        
        try:
            missions = self.db.get_missions(status=status, limit=limit)
            
            if not missions:
                print("📭 No missions found")
                return
            
            for mission in missions:
                urgency_icon = {
                    'CRITICAL': '🔥',
                    'HIGH': '⚠️',
                    'MEDIUM': '⭐',
                    'LOW': '📋',
                    'INFO': 'ℹ️'
                }.get(mission['urgency'], '❓')
                
                status_icon = {
                    'NEW': '🆕',
                    'IN_PROGRESS': '🔄',
                    'COMPLETED': '✅',
                    'CANCELLED': '❌'
                }.get(mission['status'], '❓')
                
                created = datetime.fromisoformat(mission['created_at']).strftime('%m/%d %H:%M')
                
                print(f"{status_icon} {urgency_icon} {mission['mission_id']}")
                print(f"    {mission['title']}")
                print(f"    Created: {created} | Urgency: {mission['urgency']} | Status: {mission['status']}")
                
                if mission['deadline']:
                    print(f"    Deadline: {mission['deadline']}")
                
                print()
        
        except Exception as e:
            print(f"❌ Error listing missions: {e}")
    
    def show_mission(self, mission_id: str):
        """Show detailed mission information"""
        print(f"🎯 MISSION DETAILS: {mission_id}")
        print("=" * 50)
        
        try:
            missions = self.db.get_missions()
            mission = next((m for m in missions if m['mission_id'] == mission_id), None)
            
            if not mission:
                print(f"❌ Mission {mission_id} not found")
                return
            
            print(f"Title: {mission['title']}")
            print(f"Urgency: {mission['urgency']}")
            print(f"Status: {mission['status']}")
            print(f"Created: {mission['created_at']}")
            
            if mission['deadline']:
                print(f"Deadline: {mission['deadline']}")
            
            if mission['completed_at']:
                print(f"Completed: {mission['completed_at']}")
            
            print(f"\nAction Required:")
            print(f"{mission['action_required']}")
            
            print(f"\nContext:")
            print(f"{mission['context']}")
            
            if mission['people_involved']:
                people = json.loads(mission['people_involved'])
                print(f"\nPeople Involved: {', '.join(people)}")
            
            print(f"\nEmail ID: {mission['email_id']}")
            
        except Exception as e:
            print(f"❌ Error showing mission: {e}")
    
    def mark_complete(self, mission_id: str):
        """Mark mission as completed"""
        try:
            self.db.update_mission_status(mission_id, 'COMPLETED')
            print(f"Mission {mission_id} completed")
        except Exception as e:
            print(f"Error: {e}")
    
    def mark_cancelled(self, mission_id: str):
        """Mark mission as cancelled"""
        try:
            self.db.update_mission_status(mission_id, 'CANCELLED')
            print(f"Mission {mission_id} cancelled")
        except Exception as e:
            print(f"Error: {e}")
    
    def check_emails(self):
        """Run one email check cycle"""
        print("📧 Running email check cycle...")
        try:
            monitor = EmailMonitor(check_interval_minutes=5)
            monitor.run_check_cycle()
            print("✅ Email check completed")
        except Exception as e:
            print(f"❌ Error checking emails: {e}")
    
    
    def start_monitoring(self, interval: int = 5):
        """Start continuous email monitoring"""
        print(f"🚀 Starting email monitoring (interval: {interval} minutes)...")
        print("Press Ctrl+C to stop")
        
        try:
            monitor = EmailMonitor(check_interval_minutes=interval)
            monitor.start_monitoring()
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
        except Exception as e:
            print(f"❌ Error starting monitoring: {e}")
    
    def print_mission(self, mission_id: str):
        """Reprint a mission briefing"""
        try:
            missions = self.db.get_missions()
            mission = next((m for m in missions if m['mission_id'] == mission_id), None)
            
            if not mission:
                print(f"❌ Mission {mission_id} not found")
                return
            
            # Reconstruct analysis format for printer
            analysis = json.loads(mission['raw_analysis'])
            
            printer = PrinterService(fallback_to_file=True)
            success = printer.print_mission(analysis, "Agent Roshin")
            
            if success:
                print(f"Mission {mission_id} printed")
            else:
                print(f"Failed to print mission {mission_id}")
            
            printer.close()
            
        except Exception as e:
            print(f"❌ Error reprinting mission: {e}")


def main():
    parser = argparse.ArgumentParser(description='PI2PRINTER Command Line Interface')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # List missions command
    list_parser = subparsers.add_parser('list', help='List recent missions')
    list_parser.add_argument('--status', choices=['NEW', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED'],
                            help='Filter by mission status')
    list_parser.add_argument('--limit', type=int, default=10, help='Number of missions to show')
    
    # Show mission command
    show_parser = subparsers.add_parser('show', help='Show mission details')
    show_parser.add_argument('mission_id', help='Mission ID to show')
    
    # Complete mission command
    complete_parser = subparsers.add_parser('complete', help='Mark mission as completed')
    complete_parser.add_argument('mission_id', help='Mission ID to complete')
    
    # Cancel mission command
    cancel_parser = subparsers.add_parser('cancel', help='Mark mission as cancelled')
    cancel_parser.add_argument('mission_id', help='Mission ID to cancel')
    
    # Check emails command
    subparsers.add_parser('check', help='Run one email check cycle')
    
    
    # Print mission command
    print_parser = subparsers.add_parser('print', help='Reprint a mission briefing')
    print_parser.add_argument('mission_id', help='Mission ID to reprint')
    
    # Monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Start continuous email monitoring')
    monitor_parser.add_argument('--interval', '-i', type=int, default=5,
                               help='Check interval in minutes (default: 5)')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = Pi2PrinterCLI()
    
    try:
        if args.command == 'status':
            cli.status()
        elif args.command == 'list':
            cli.list_missions(status=args.status, limit=args.limit)
        elif args.command == 'show':
            cli.show_mission(args.mission_id)
        elif args.command == 'complete':
            cli.mark_complete(args.mission_id)
        elif args.command == 'cancel':
            cli.mark_cancelled(args.mission_id)
        elif args.command == 'check':
            cli.check_emails()
        elif args.command == 'print':
            cli.print_mission(args.mission_id)
        elif args.command == 'monitor':
            cli.start_monitoring(interval=args.interval)
        else:
            parser.print_help()
    
    except Exception as e:
        print(f"❌ Command failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()