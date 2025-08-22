import sqlite3
import csv
import os
import argparse

def create_database(db_path):
    """Create the SQLite database and tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create Words table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL UNIQUE,
            rank INTEGER NOT NULL CHECK(rank BETWEEN 1 AND 2800),
            step INTEGER NOT NULL CHECK(step BETWEEN 1 AND 28),
            level INTEGER NOT NULL CHECK(level BETWEEN 1 AND 5)
        )
    """)
    
    # Create StudentWords table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS StudentWords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            word_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('learning','mastered')) DEFAULT 'learning',
            UNIQUE(student_name, word_id),
            FOREIGN KEY(word_id) REFERENCES Words(id) ON DELETE CASCADE
        )
    """)
    
    # Create indexes for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_rank ON Words(rank)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_studentwords_student ON StudentWords(student_name)")
    
    conn.commit()
    conn.close()

def compute_step_level(rank):
    """Compute step and level from rank."""
    step = ((rank - 1) // 100) + 1
    level = (((rank - 1) % 100) // 20) + 1
    return step, level

def import_words(csv_path, db_path):
    """Import words from CSV file and compute step/level."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header row
        
        for row in reader:
            if len(row) >= 2:
                try:
                    rank = int(row[0])
                    word = row[1].strip()
                    
                    # Validate rank
                    if not (1 <= rank <= 2800):
                        print(f"Warning: Skipping invalid rank {rank} for word '{word}'")
                        continue
                    
                    # Compute step and level
                    step, level = compute_step_level(rank)
                    
                    # Upsert word into database
                    cursor.execute("""
                        INSERT INTO Words (word, rank, step, level)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(word) DO UPDATE SET
                            rank=excluded.rank,
                            step=excluded.step,
                            level=excluded.level
                    """, (word, rank, step, level))
                except ValueError:
                    print(f"Warning: Skipping invalid data row: {row}")
                    continue
    
    conn.commit()
    conn.close()

def main():
    parser = argparse.ArgumentParser(description='Setup Pathway database and import words')
    parser.add_argument('--csv', default='words_rank.csv', help='Path to CSV file with words and ranks')
    args = parser.parse_args()
    
    db_path = 'pathway.db'
    csv_path = args.csv
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file '{csv_path}' not found.")
        return
    
    print("Creating database...")
    create_database(db_path)
    
    print("Importing words...")
    import_words(csv_path, db_path)
    
    print("Database setup complete!")

if __name__ == '__main__':
    main()