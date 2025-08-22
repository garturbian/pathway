import sqlite3
import pyperclip
import argparse
import sys

def get_learning_words(student_name, db_path='pathway.db'):
    """Get all learning words for a student, grouped by step and level."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT w.word, w.step, w.level, w.rank
        FROM StudentWords sw
        JOIN Words w ON sw.word_id = w.id
        WHERE sw.student_name = ? AND sw.status = 'learning'
        ORDER BY w.step, w.level, w.rank
    """, (student_name,))
    
    words = cursor.fetchall()
    conn.close()
    
    return words

def format_clipboard_output(student_name, words):
    """Format the output for clipboard."""
    if not words:
        return f"No learning words found for {student_name}."
    
    # Group words by step and level
    grouped = {}
    for word, step, level, rank in words:
        key = (step, level)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(word)
    
    # Format output
    lines = [f"Currently Learning — {student_name}"]
    
    for (step, level), word_list in sorted(grouped.items()):
        start_rank = ((step - 1) * 100) + ((level - 1) * 20) + 1
        end_rank = start_rank + 19
        lines.append(f"\nStep {step} - Level {level} (Ranks {start_rank}–{end_rank}):")
        lines.append(", ".join(word_list))
    
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description='Retrieve student learning words')
    parser.add_argument('--student', help='Student name')
    args = parser.parse_args()
    
    # Prompt for student name if not provided
    if args.student is None:
        args.student = input("Enter student name: ").strip()
    
    if not args.student:
        print("Student name cannot be empty.")
        sys.exit(1)
    
    # Get learning words
    words = get_learning_words(args.student)
    
    # Format and copy to clipboard
    output = format_clipboard_output(args.student, words)
    pyperclip.copy(output)
    
    # Also print to console
    print(output)
    print("\nCopied to clipboard!")

if __name__ == '__main__':
    main()