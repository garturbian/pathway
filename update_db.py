import sqlite3
import argparse

def update_database(db_path='pathway.db'):
    """Update the database schema to support special words and rewards."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create SpecialWords table for words not in the 2800-word database
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS SpecialWords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    """)
    
    # Create StudentSpecialWords table to track special words for students
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS StudentSpecialWords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            special_word_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('learning','mastered')) DEFAULT 'learning',
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mastered_date TIMESTAMP NULL,
            UNIQUE(student_name, special_word_id),
            FOREIGN KEY(special_word_id) REFERENCES SpecialWords(id) ON DELETE CASCADE
        )
    """)
    
    # Create Rewards table to track student achievements
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            word_id INTEGER NULL,  -- For regular words
            special_word_id INTEGER NULL,  -- For special words
            reward_type TEXT NOT NULL,  -- 'word_mastered', 'special_word_mastered', etc.
            reward_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            CHECK ((word_id IS NOT NULL AND special_word_id IS NULL) OR 
                   (word_id IS NULL AND special_word_id IS NOT NULL))
        )
    """)
    
    # Add indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_special_words_word ON SpecialWords(word)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_student_special_words ON StudentSpecialWords(student_name, status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rewards_student ON Rewards(student_name)")
    
    conn.commit()
    conn.close()
    
    print("Database updated successfully!")

def main():
    parser = argparse.ArgumentParser(description='Update Pathway database schema')
    parser.add_argument('--db', default='pathway.db', help='Path to database file')
    args = parser.parse_args()
    
    update_database(args.db)

if __name__ == '__main__':
    main()