import sqlite3
import json

def get_learning_words(student_name, db_path='pathway.db'):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get regular learning words
    cursor.execute("""
        SELECT w.id, w.word, w.step, w.level, sw.status
        FROM StudentWords sw
        JOIN Words w ON sw.word_id = w.id
        WHERE sw.student_name = ? AND sw.status = 'learning'
        ORDER BY w.step, w.level, w.rank
    """, (student_name,))
    
    regular_words = [dict(row) for row in cursor.fetchall()]
    
    # Get special learning words
    cursor.execute("""
        SELECT sp.id, sp.word, NULL as step, NULL as level, sw.status, 'special' as word_type, sw.special_word_id
        FROM StudentSpecialWords sw
        JOIN SpecialWords sp ON sw.special_word_id = sp.id
        WHERE sw.student_name = ? AND sw.status = 'learning'
        ORDER BY sw.added_date
    """, (student_name,))
    
    special_words = [dict(row) for row in cursor.fetchall()]
    
    # Combine and sort words
    all_words = regular_words + special_words
    
    conn.close()
    
    return all_words

# Test with Yumi
words = get_learning_words('Yumi')
print(json.dumps(words, indent=2))