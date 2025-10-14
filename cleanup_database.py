#!/usr/bin/env python3
"""
Database Cleanup Utility for Exotel-Slack System
Clears stale or failed processing records to allow retry
"""

import sqlite3
import os
from datetime import datetime, timedelta

def cleanup_database(db_path="processed_calls.db"):
    """Clean up stale processing records and failed calls"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check current records
        cursor.execute("SELECT COUNT(*) FROM processed_calls")
        total_records = cursor.fetchone()[0]
        print(f"📊 Total records in database: {total_records}")
        
        # Check records by status
        cursor.execute("SELECT status, COUNT(*) FROM processed_calls GROUP BY status")
        status_counts = cursor.fetchall()
        print("📈 Records by status:")
        for status, count in status_counts:
            print(f"   {status}: {count}")
        
        # Check records by slack_posted
        cursor.execute("SELECT slack_posted, COUNT(*) FROM processed_calls GROUP BY slack_posted")
        slack_counts = cursor.fetchall()
        print("📈 Records by Slack posting:")
        for posted, count in slack_counts:
            print(f"   Posted: {posted}: {count}")
        
        # Find stale processing records (older than 1 hour)
        one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        cursor.execute("""
            SELECT call_id, processed_at, status, slack_posted 
            FROM processed_calls 
            WHERE status = 'processing' AND processed_at < ?
        """, (one_hour_ago,))
        
        stale_records = cursor.fetchall()
        print(f"\n🕐 Stale processing records (older than 1 hour): {len(stale_records)}")
        
        if stale_records:
            print("📋 Stale records:")
            for call_id, processed_at, status, slack_posted in stale_records:
                print(f"   {call_id}: {processed_at} - {status} (Slack: {slack_posted})")
        
        # Find failed records (not posted to Slack)
        cursor.execute("""
            SELECT call_id, processed_at, status, slack_posted 
            FROM processed_calls 
            WHERE slack_posted = 0 AND status != 'processing'
        """)
        
        failed_records = cursor.fetchall()
        print(f"\n❌ Failed records (not posted to Slack): {len(failed_records)}")
        
        if failed_records:
            print("📋 Failed records:")
            for call_id, processed_at, status, slack_posted in failed_records:
                print(f"   {call_id}: {processed_at} - {status} (Slack: {slack_posted})")
        
        # Show recent calls (last hour) - these are the ones that matter for duplicate detection
        cursor.execute("""
            SELECT call_id, processed_at, status, slack_posted 
            FROM processed_calls 
            WHERE processed_at > ?
            ORDER BY processed_at DESC
        """, (one_hour_ago,))
        
        recent_records = cursor.fetchall()
        print(f"\n⏰ Recent calls (last hour): {len(recent_records)}")
        
        if recent_records:
            print("📋 Recent calls (these affect duplicate detection):")
            for call_id, processed_at, status, slack_posted in recent_records:
                print(f"   {call_id}: {processed_at} - {status} (Slack: {slack_posted})")
        
        # Ask for cleanup action
        print(f"\n🧹 Cleanup Options:")
        print("1. Reset stale processing records (allow retry)")
        print("2. Delete failed records completely")
        print("3. Reset all non-posted records")
        print("4. Show specific call details")
        print("5. Exit without changes")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            # Reset stale processing records
            cursor.execute("""
                UPDATE processed_calls 
                SET status = 'failed', processed_at = ?
                WHERE status = 'processing' AND processed_at < ?
            """, (datetime.utcnow().isoformat(), one_hour_ago))
            
            affected = cursor.rowcount
            conn.commit()
            print(f"✅ Reset {affected} stale processing records")
            
        elif choice == "2":
            # Delete failed records
            cursor.execute("DELETE FROM processed_calls WHERE slack_posted = 0 AND status != 'processing'")
            affected = cursor.rowcount
            conn.commit()
            print(f"✅ Deleted {affected} failed records")
            
        elif choice == "3":
            # Reset all non-posted records
            cursor.execute("""
                UPDATE processed_calls 
                SET status = 'failed', processed_at = ?
                WHERE slack_posted = 0
            """, (datetime.utcnow().isoformat()))
            
            affected = cursor.rowcount
            conn.commit()
            print(f"✅ Reset {affected} non-posted records")
            
        elif choice == "4":
            # Show specific call details
            call_id = input("Enter call ID to check: ").strip()
            cursor.execute("""
                SELECT call_id, from_number, to_number, processed_at, status, slack_posted, transcription_text
                FROM processed_calls 
                WHERE call_id = ?
            """, (call_id,))
            
            record = cursor.fetchone()
            if record:
                print(f"\n📋 Call Details for {call_id}:")
                print(f"   From: {record[1]}")
                print(f"   To: {record[2]}")
                print(f"   Processed At: {record[3]}")
                print(f"   Status: {record[4]}")
                print(f"   Slack Posted: {record[5]}")
                print(f"   Transcription: {record[6][:100]}..." if record[6] else "   Transcription: None")
            else:
                print(f"❌ Call {call_id} not found in database")
        
        elif choice == "5":
            print("👋 Exiting without changes")
        
        else:
            print("❌ Invalid choice")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("🧹 Exotel-Slack Database Cleanup Utility")
    print("=" * 50)
    cleanup_database()
