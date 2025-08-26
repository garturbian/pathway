import sqlite3
import json
import requests
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

DATABASE = 'pathway.db'
OLLAMA_URL = 'http://localhost:11434/api/generate'  # Default Ollama API endpoint
OLLAMA_MODEL = 'qwen2.5'  # Changed to qwen2.5 model

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

@app.route('/api/students', methods=['GET'])
def get_students():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT DISTINCT student_name FROM StudentProgress
        UNION
        SELECT DISTINCT student_name FROM StudentWords
        UNION
        SELECT DISTINCT student_name FROM StudentSpecialWords
        ORDER BY student_name
    """)
    
    students = [row['student_name'] for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'students': students})

@app.route('/api/student/<student_name>', methods=['DELETE'])
def delete_student(student_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete all data associated with the student
    cursor.execute("DELETE FROM StudentWords WHERE student_name = ?", (student_name,))
    cursor.execute("DELETE FROM StudentSpecialWords WHERE student_name = ?", (student_name,))
    cursor.execute("DELETE FROM StudentProgress WHERE student_name = ?", (student_name,))
    cursor.execute("DELETE FROM Rewards WHERE student_name = ?", (student_name,))
    
    conn.commit()
    conn.close()
    
    return jsonify({'message': f'Student "{student_name}" and all associated data have been deleted'})

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

@app.route('/api/student/<student_name>/special_words/batch', methods=['POST'])
def add_special_words_batch(student_name):
    data = request.get_json()
    words = data.get('words', [])
    notes = data.get('notes', '')
    force_add = data.get('force_add', False)  # New parameter to force add existing words
    
    if not words or not isinstance(words, list):
        return jsonify({'error': 'Words list is required'}), 400
    
    results = {
        'added': [],
        'existing': [],  # New category for existing words
        'errors': []
    }
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for word in words:
        try:
            if not word:
                results['errors'].append({'word': word, 'error': 'Word is required'})
                continue
                
            # First check if the word already exists in the main Words table
            cursor.execute("SELECT word, step, level FROM Words WHERE word = ?", (word,))
            existing_word = cursor.fetchone()
            
            if existing_word:
                existing_info = {
                    'word': word,
                    'step': existing_word['step'],
                    'level': existing_word['level']
                }
                
                # If force_add is True, we'll add it as a special word anyway
                if force_add:
                    # Insert special word even though it exists in main list
                    cursor.execute("""
                        INSERT OR IGNORE INTO SpecialWords (word, notes)
                        VALUES (?, ?)
                    """, (word, notes))
                    
                    # Get the special word ID
                    cursor.execute("SELECT id FROM SpecialWords WHERE word = ?", (word,))
                    special_word_row = cursor.fetchone()
                    
                    if not special_word_row:
                        results['errors'].append({'word': word, 'error': 'Failed to add special word'})
                        continue
                    
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
                    
                    results['added'].append({'word': word, 'id': special_word_id, 'existing': True})
                else:
                    # Just inform user about existing word
                    results['existing'].append(existing_info)
                continue
            
            # Insert special word if it doesn't exist in main list
            cursor.execute("""
                INSERT OR IGNORE INTO SpecialWords (word, notes)
                VALUES (?, ?)
            """, (word, notes))
            
            # Get the special word ID
            cursor.execute("SELECT id FROM SpecialWords WHERE word = ?", (word,))
            special_word_row = cursor.fetchone()
            
            if not special_word_row:
                results['errors'].append({'word': word, 'error': 'Failed to add special word'})
                continue
            
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
            
            results['added'].append({'word': word, 'id': special_word_id})
            
        except Exception as e:
            results['errors'].append({'word': word, 'error': str(e)})
    
    conn.commit()
    conn.close()
    
    message = f"Added {len(results['added'])} special word(s)"
    if results['existing']:
        message += f", {len(results['existing'])} word(s) already exist in main list"
    if results['errors']:
        message += f", {len(results['errors'])} error(s)"
    
    return jsonify({
        'message': message,
        'results': results
    })

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

@app.route('/api/student/<student_name>/special_words')
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

@app.route('/api/student/<student_name>/generate_story', methods=['POST'])
def generate_story(student_name):
    # Get the learning words for the student
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get regular learning words
    cursor.execute("""
        SELECT w.word
        FROM StudentWords sw
        JOIN Words w ON sw.word_id = w.id
        WHERE sw.student_name = ? AND sw.status = 'learning'
        ORDER BY w.step, w.level, w.rank
    """, (student_name,))
    
    regular_words = [row['word'] for row in cursor.fetchall()]
    
    # Get special learning words
    cursor.execute("""
        SELECT sp.word
        FROM StudentSpecialWords sw
        JOIN SpecialWords sp ON sw.special_word_id = sp.id
        WHERE sw.student_name = ? AND sw.status = 'learning'
        ORDER BY sw.added_date
    """, (student_name,))
    
    special_words = [row['word'] for row in cursor.fetchall()]
    
    conn.close()
    
    # Combine all learning words
    all_words = regular_words + special_words
    
    if not all_words:
        return jsonify({'error': 'No learning words found for this student'}), 400
    
    # Create the prompt for Ollama
    words_list = ', '.join(all_words)
    prompt = f"Write a 200 word story that will be easy for an A2 level ESL learner to understand. Students at this level have a very limited vocabulary. Use these words in the story: {words_list}. Include the word list."
    
    # Prepare the request to Ollama
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        # Send request to Ollama
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)  # 60 second timeout
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        story = result.get('response', 'Sorry, I could not generate a story.')
        
        return jsonify({'story': story})
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request to Ollama timed out. Please check if Ollama is running and try again.'}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Error connecting to Ollama: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Error generating story: {str(e)}'}), 500

@app.route('/api/student/<student_name>/generate_questions', methods=['POST'])
def generate_questions(student_name):
    # Get the learning words for the student
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get regular learning words
    cursor.execute("""
        SELECT w.word
        FROM StudentWords sw
        JOIN Words w ON sw.word_id = w.id
        WHERE sw.student_name = ? AND sw.status = 'learning'
        ORDER BY w.step, w.level, w.rank
    """, (student_name,))
    
    regular_words = [row['word'] for row in cursor.fetchall()]
    
    # Get special learning words
    cursor.execute("""
        SELECT sp.word
        FROM StudentSpecialWords sw
        JOIN SpecialWords sp ON sw.special_word_id = sp.id
        WHERE sw.student_name = ? AND sw.status = 'learning'
        ORDER BY sw.added_date
    """, (student_name,))
    
    special_words = [row['word'] for row in cursor.fetchall()]
    
    conn.close()
    
    # Combine all learning words
    all_words = regular_words + special_words
    
    if not all_words:
        return jsonify({'error': 'No learning words found for this student'}), 400
    
    # Create the prompt for Ollama
    words_list = ', '.join(all_words)
    prompt = f"Create multiple choice questions to test a learner's understanding of the following words. The student is an A2 level ESL learner with a limited vocabulary. Restrict your word choice to make it easy for an A2 level ESL learner to understand. Create one question for EACH word in the list. Number the questions sequentially from 1 to {len(all_words)}. In each question, the student will select which word best fills the blank. Provide exactly 4 choices: one correct answer and three distractors (incorrect options). Do NOT indicate the correct answer in the quiz. Use simple numbering like '1:' instead of 'Question 1:'. Do NOT use labels like 'Answer Choices:'. Format the options as 'A) word', 'B) word', 'C) word', 'D) word'. Put the answers in a separate section at the end of your response. Do NOT use # or * in the response. Test these words: {words_list}"
    
    # Prepare the request to Ollama
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        # Send request to Ollama
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)  # 60 second timeout
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        questions = result.get('response', 'Sorry, I could not generate questions.')
        
        return jsonify({'questions': questions})
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request to Ollama timed out. Please check if Ollama is running and try again.'}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Error connecting to Ollama: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Error generating questions: {str(e)}'}), 500

if __name__ == '__main__':
    # Check if database exists, if not, create it
    if not os.path.exists(DATABASE):
        print("Database not found. Please run setup_db.py first.")
        exit(1)
    
    app.run(debug=True, port=5001)