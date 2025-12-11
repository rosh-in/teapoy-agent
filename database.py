#!/usr/bin/env python3
"""
PI2PRINTER Database Setup and Utilities
SQLite database for mission and email tracking
"""

import sqlite3
import json
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from pathlib import Path

DATABASE_FILE = "pi2printer.db"

class Database:
    def __init__(self, db_file: str = DATABASE_FILE):
        """Initialize database connection"""
        self.db_file = db_file
        self.init_database()
    
    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Create database tables if they don't exist"""
        with self.get_connection() as conn:
            # Missions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS missions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT UNIQUE NOT NULL,
                    email_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    urgency TEXT NOT NULL CHECK (urgency IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')),
                    deadline DATETIME,
                    action_required TEXT,
                    context TEXT,
                    people_involved TEXT, -- JSON array
                    google_task_id TEXT,
                    status TEXT DEFAULT 'NEW' CHECK (status IN ('NEW', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    raw_analysis TEXT -- Full JSON from Gemini
                )
            """)
            
            # Processed emails table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_emails (
                    email_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    date_received TEXT,
                    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    has_task BOOLEAN NOT NULL DEFAULT 0,
                    mission_id TEXT,
                    FOREIGN KEY (mission_id) REFERENCES missions (mission_id)
                )
            """)
            
            # System config table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Print queue table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS print_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mission_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'PRINTING', 'COMPLETED', 'FAILED')),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    printed_at DATETIME,
                    error_message TEXT,
                    FOREIGN KEY (mission_id) REFERENCES missions (mission_id)
                )
            """)
            
            conn.commit()
        
        print("✅ Database initialized successfully")
    
    def create_mission(self, analysis: Dict[str, Any], email_data: Dict[str, str]) -> str:
        """Create a new mission from analysis data"""
        if not analysis.get('has_task'):
            return None
        
        mission = analysis['mission_briefing']
        mission_id = mission['mission_id']
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO missions (
                    mission_id, email_id, title, urgency, deadline,
                    action_required, context, people_involved, raw_analysis
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mission_id,
                email_data['id'],
                mission['title'],
                mission['urgency'],
                mission.get('deadline'),
                mission['action_required'],
                mission['context'],
                json.dumps(mission.get('people_involved', [])),
                json.dumps(analysis)
            ))
            conn.commit()
        
        print(f"✅ Mission created: {mission_id}")
        return mission_id
    
    def mark_email_processed(self, email_data: Dict[str, str], has_task: bool = False, mission_id: str = None):
        """Mark email as processed"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO processed_emails (
                    email_id, subject, sender, date_received, has_task, mission_id
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                email_data['id'],
                email_data.get('subject', 'No Subject'),
                email_data.get('from', 'Unknown'),
                email_data.get('date', ''),
                has_task,
                mission_id
            ))
            conn.commit()
    
    def is_email_processed(self, email_id: str) -> bool:
        """Check if email has already been processed"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM processed_emails WHERE email_id = ?",
                (email_id,)
            )
            return cursor.fetchone()[0] > 0
    
    def get_missions(self, status: str = None, limit: int = None) -> List[Dict]:
        """Get missions with optional filtering"""
        query = "SELECT * FROM missions"
        params = []
        
        if status:
            query += " WHERE status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_mission_status(self, mission_id: str, status: str, google_task_id: str = None):
        """Update mission status"""
        with self.get_connection() as conn:
            if status == 'COMPLETED':
                conn.execute("""
                    UPDATE missions 
                    SET status = ?, completed_at = ?, google_task_id = COALESCE(?, google_task_id)
                    WHERE mission_id = ?
                """, (status, datetime.now(timezone.utc).isoformat(), google_task_id, mission_id))
            else:
                conn.execute("""
                    UPDATE missions 
                    SET status = ?, google_task_id = COALESCE(?, google_task_id)
                    WHERE mission_id = ?
                """, (status, google_task_id, mission_id))
            conn.commit()
    
    def add_to_print_queue(self, mission_id: str, content: str):
        """Add mission to print queue"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO print_queue (mission_id, content)
                VALUES (?, ?)
            """, (mission_id, content))
            conn.commit()
    
    def get_pending_prints(self) -> List[Dict]:
        """Get pending print jobs"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM print_queue 
                WHERE status = 'PENDING' 
                ORDER BY created_at ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_print_status(self, print_id: int, status: str, error_message: str = None):
        """Update print job status"""
        with self.get_connection() as conn:
            if status == 'COMPLETED':
                conn.execute("""
                    UPDATE print_queue 
                    SET status = ?, printed_at = ?
                    WHERE id = ?
                """, (status, datetime.now(timezone.utc).isoformat(), print_id))
            else:
                conn.execute("""
                    UPDATE print_queue 
                    SET status = ?, error_message = ?
                    WHERE id = ?
                """, (status, error_message, print_id))
            conn.commit()
    
    def get_config(self, key: str, default: str = None) -> str:
        """Get configuration value"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT value FROM system_config WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return row[0] if row else default
    
    def set_config(self, key: str, value: str):
        """Set configuration value"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO system_config (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now(timezone.utc).isoformat()))
            conn.commit()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        with self.get_connection() as conn:
            stats = {}
            
            # Mission counts by status
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM missions 
                GROUP BY status
            """)
            stats['missions_by_status'] = dict(cursor.fetchall())
            
            # Mission counts by urgency
            cursor = conn.execute("""
                SELECT urgency, COUNT(*) as count 
                FROM missions 
                GROUP BY urgency
            """)
            stats['missions_by_urgency'] = dict(cursor.fetchall())
            
            # Recent activity
            cursor = conn.execute("""
                SELECT COUNT(*) as count
                FROM missions 
                WHERE created_at > datetime('now', '-24 hours')
            """)
            stats['missions_last_24h'] = cursor.fetchone()[0]
            
            # Email processing stats
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_emails,
                    SUM(has_task) as emails_with_tasks
                FROM processed_emails
            """)
            row = cursor.fetchone()
            stats['total_emails_processed'] = row[0]
            stats['emails_with_tasks'] = row[1]
            
            return stats

def test_database():
    """Test database functionality"""
    print("🧪 Testing database functionality...")
    
    # Create test database
    db = Database("test.db")
    
    # Test email processing
    test_email = {
        'id': 'test123',
        'subject': 'Test Email',
        'from': 'test@example.com',
        'date': '2025-12-10'
    }
    
    db.mark_email_processed(test_email, has_task=False)
    
    # Test mission creation
    test_analysis = {
        'has_task': True,
        'mission_briefing': {
            'mission_id': 'MI-TEST001',
            'title': 'Test Mission',
            'urgency': 'MEDIUM',
            'deadline': None,
            'action_required': 'Complete test',
            'context': 'This is a test mission',
            'people_involved': ['test@example.com']
        }
    }
    
    mission_id = db.create_mission(test_analysis, test_email)
    
    # Test mission retrieval
    missions = db.get_missions(limit=5)
    print(f"   Created mission: {missions[0]['title']}")
    
    # Test stats
    stats = db.get_stats()
    print(f"   Statistics: {stats}")
    
    # Cleanup
    Path("test.db").unlink(missing_ok=True)
    
    print("✅ Database tests passed!")

if __name__ == '__main__':
    test_database()