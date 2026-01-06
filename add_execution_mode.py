#!/usr/bin/env python3
"""
Add execution_mode column to scans table for local SQLite database
"""
import sqlite3
import os

def add_execution_mode_column():
    """Add execution_mode column to scans table"""
    db_path = "pentest_brain.db"
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found. Please run the application first to create it.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(scans)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'execution_mode' in columns:
            print("execution_mode column already exists")
            return
        
        # Add the column
        cursor.execute("""
            ALTER TABLE scans 
            ADD COLUMN execution_mode TEXT DEFAULT 'report_only'
        """)
        
        conn.commit()
        print("Successfully added execution_mode column to scans table")
        
    except Exception as e:
        print(f"Error adding execution_mode column: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    add_execution_mode_column()