import sqlite3
import argparse

def update_database_with_student_progress(db_path='pathway.db'):
    """Update the database schema to track student progress (step and level)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create a separate table for student progress to track their current position on the pathway
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS StudentProgress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL UNIQUE,
            current_step INTEGER NOT NULL DEFAULT 1 CHECK(current_step BETWEEN 1 AND 28),
            current_level INTEGER NOT NULL DEFAULT 1 CHECK(current_level BETWEEN 1 AND 5),
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create index for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_progress_name ON StudentProgress(student_name)")
    
    conn.commit()
    conn.close()
    
    print("Database updated successfully with student progress tracking!")

def main():
    parser = argparse.ArgumentParser(description='Update Pathway database schema with student progress tracking')
    parser.add_argument('--db', default='pathway.db', help='Path to database file')
    args = parser.parse_args()
    
    update_database_with_student_progress(args.db)

if __name__ == '__main__':
    main()