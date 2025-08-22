import sqlite3
import json
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

DATABASE = 'pathway.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template_string(open('pathway.html').read())

@app.route('/api/student', methods=['POST'])
def set_student():
    data = request.get_json()
    student_name = data.get('student_name')
    
    if not student_name:
        return jsonify({'error': 'Student name is required'}), 400
    
    return jsonify({'message': f'Student set to: {student_name}'})

@app.route('/api/words/step/<int:step>/level/<int:level>')
def get_words_by_step_level(step, level):
    if not (1 <= step <= 28) or not (1 <= level <= 5):
        return jsonify({'error': 'Invalid step or level'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, word FROM Words 
        WHERE step = ? AND level = ? 
        ORDER BY rank
    """, (step, level))
    
    words = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'words': words})

@app.route('/api/student/<student_name>/learning_words', methods=['GET'])
def get_learning_words(student_name):
    conn = get_db_connection()
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
        SELECT sp.id, sp.word, NULL as step, NULL as level, sw.status, 'special' as word_type
        FROM StudentSpecialWords sw
        JOIN SpecialWords sp ON sw.special_word_id = sp.id
        WHERE sw.student_name = ? AND sw.status = 'learning'
        ORDER BY sw.added_date
    """, (student_name,))
    
    special_words = [dict(row) for row in cursor.fetchall()]
    
    # Combine and sort words
    all_words = regular_words + special_words
    
    conn.close()
    
    return jsonify({'words': all_words})

@app.route('/api/student/<student_name>/learning_words', methods=['POST'])
def add_learning_words(student_name):
    data = request.get_json()
    word_ids = data.get('word_ids', [])
    special_word_ids = data.get('special_word_ids', [])
    
    if not word_ids and not special_word_ids:
        return jsonify({'error': 'No word IDs provided'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Add regular words
    for word_id in word_ids:
        cursor.execute("""
            INSERT OR IGNORE INTO StudentWords (student_name, word_id, status)
            VALUES (?, ?, 'learning')
        """, (student_name, word_id))
    
    # Add special words
    for special_word_id in special_word_ids:
        cursor.execute("""
            INSERT OR IGNORE INTO StudentSpecialWords (student_name, special_word_id, status)
            VALUES (?, ?, 'learning')
        """, (student_name, special_word_id))
    
    conn.commit()
    conn.close()
    
    total_added = len(word_ids) + len(special_word_ids)
    return jsonify({'message': f'Added {total_added} word(s) to learning list'})

@app.route('/api/student/<student_name>/learning_words/<int:word_id>', methods=['DELETE'])
def remove_learning_word(student_name, word_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM StudentWords
        WHERE student_name = ? AND word_id = ?
    """, (student_name, word_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Word removed from learning list'})

@app.route('/api/student/<student_name>/learning_special_words/<int:special_word_id>', methods=['DELETE'])
def remove_learning_special_word(student_name, special_word_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM StudentSpecialWords
        WHERE student_name = ? AND special_word_id = ?
    """, (student_name, special_word_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Special word removed from learning list'})

@app.route('/api/student/<student_name>/learning_words/<int:word_id>/master', methods=['POST'])
def master_learning_word(student_name, word_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE StudentWords
        SET status = 'mastered'
        WHERE student_name = ? AND word_id = ?
    """, (student_name, word_id))
    
    # Add to rewards
    cursor.execute("""
        INSERT INTO Rewards (student_name, word_id, reward_type, notes)
        VALUES (?, ?, 'word_mastered', 'Mastered word')
    """, (student_name, word_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Word marked as mastered'})

@app.route('/api/student/<student_name>/learning_words/<int:word_id>/learning', methods=['POST'])
def learning_learning_word(student_name, word_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE StudentWords
        SET status = 'learning'
        WHERE student_name = ? AND word_id = ?
    """, (student_name, word_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Word marked as learning'})

@app.route('/api/student/<student_name>/progress', methods=['GET'])
def get_student_progress(student_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT current_step, current_level
        FROM StudentProgress
        WHERE student_name = ?
    """, (student_name,))
    
    progress = cursor.fetchone()
    conn.close()
    
    if progress:
        return jsonify({
            'step': progress['current_step'],
            'level': progress['current_level']
        })
    else:
        # Return default values if no progress is set
        return jsonify({
            'step': 1,
            'level': 1
        })

@app.route('/api/student/<student_name>/progress', methods=['POST'])
def set_student_progress(student_name):
    data = request.get_json()
    step = data.get('step')
    level = data.get('level')
    
    if not step or not level:
        return jsonify({'error': 'Step and level are required'}), 400
    
    if not (1 <= step <= 28) or not (1 <= level <= 5):
        return jsonify({'error': 'Invalid step or level'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert or update student progress
    cursor.execute("""
        INSERT INTO StudentProgress (student_name, current_step, current_level)
        VALUES (?, ?, ?)
        ON CONFLICT(student_name) DO UPDATE SET
            current_step = excluded.current_step,
            current_level = excluded.current_level,
            last_updated = CURRENT_TIMESTAMP
    """, (student_name, step, level))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': f'Student progress updated to Step {step}, Level {level}'})

@app.route('/api/student/<student_name>/special_words/<int:special_word_id>/learning', methods=['POST'])
def learning_special_word(student_name, special_word_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE StudentSpecialWords
        SET status = 'learning', mastered_date = NULL
        WHERE student_name = ? AND special_word_id = ?
    """, (student_name, special_word_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Special word marked as learning'})

@app.route('/api/student/<student_name>/special_words', methods=['GET'])
def get_special_words(student_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT sw.id, sw.special_word_id, sw.status, sw.added_date, sw.mastered_date,
               sp.word, sp.notes
        FROM StudentSpecialWords sw
        JOIN SpecialWords sp ON sw.special_word_id = sp.id
        WHERE sw.student_name = ?
        ORDER BY sw.added_date DESC
    """, (student_name,))
    
    words = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'words': words})

@app.route('/api/student/<student_name>/special_words', methods=['POST'])
def add_special_word(student_name):
    data = request.get_json()
    word = data.get('word')
    notes = data.get('notes', '')
    
    if not word:
        return jsonify({'error': 'Word is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # First check if the word already exists in the main Words table
    cursor.execute("SELECT word, step, level FROM Words WHERE word = ?", (word,))
    existing_word = cursor.fetchone()
    
    if existing_word:
        conn.close()
        return jsonify({
            'error': f'Word "{word}" already exists in the 2800-word list',
            'step': existing_word['step'],
            'level': existing_word['level']
        }), 400
    
    # Insert special word if it doesn't exist
    cursor.execute("""
        INSERT OR IGNORE INTO SpecialWords (word, notes)
        VALUES (?, ?)
    """, (word, notes))
    
    # Get the special word ID
    cursor.execute("SELECT id FROM SpecialWords WHERE word = ?", (word,))
    special_word_row = cursor.fetchone()
    
    if not special_word_row:
        conn.close()
        return jsonify({'error': 'Failed to add special word'}), 500
    
    special_word_id = special_word_row['id']
    
    # Add to student's special words
    cursor.execute("""
        INSERT OR IGNORE INTO StudentSpecialWords (student_name, special_word_id, status)
        VALUES (?, ?, 'learning')
    """, (student_name, special_word_id))
    
    # Add to rewards
    cursor.execute("""
        INSERT INTO Rewards (student_name, special_word_id, reward_type, notes)
        VALUES (?, ?, 'special_word_added', 'Added special word')
    """, (student_name, special_word_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': f'Special word "{word}" added'})

@app.route('/api/student/<student_name>/special_words/<int:special_word_id>', methods=['DELETE'])
def remove_special_word(student_name, special_word_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        DELETE FROM StudentSpecialWords
        WHERE student_name = ? AND special_word_id = ?
    """, (student_name, special_word_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Special word removed from learning list'})

@app.route('/api/student/<student_name>/special_words/<int:special_word_id>/master', methods=['POST'])
def master_special_word(student_name, special_word_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE StudentSpecialWords
        SET status = 'mastered', mastered_date = CURRENT_TIMESTAMP
        WHERE student_name = ? AND special_word_id = ?
    """, (student_name, special_word_id))
    
    # Add to rewards
    cursor.execute("""
        INSERT INTO Rewards (student_name, special_word_id, reward_type, notes)
        VALUES (?, ?, 'special_word_mastered', 'Mastered special word')
    """, (student_name, special_word_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Special word marked as mastered'})

@app.route('/api/student/<student_name>/rewards', methods=['GET'])
def get_rewards(student_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, reward_type, reward_date, notes
        FROM Rewards
        WHERE student_name = ?
        ORDER BY reward_date DESC
    """, (student_name,))
    
    rewards = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'rewards': rewards})

@app.route('/api/special_words')
def get_special_words_list():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, word FROM SpecialWords
        ORDER BY word
    """)
    
    words = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'words': words})

if __name__ == '__main__':
    # Check if database exists, if not, create it
    if not os.path.exists(DATABASE):
        print("Database not found. Please run setup_db.py first.")
        exit(1)
    
    app.run(debug=True, port=5001)