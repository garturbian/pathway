import sqlite3
import pyperclip
import argparse
import sys

def get_words_by_step_level(step, level, db_path='pathway.db'):
    """Get words for a specific step and level."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, word FROM Words 
        WHERE step = ? AND level = ? 
        ORDER BY rank
    """, (step, level))
    
    words = cursor.fetchall()
    conn.close()
    
    return words

def save_learning_words(student_name, word_ids, db_path='pathway.db'):
    """Save selected words as 'learning' for a student."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for word_id in word_ids:
        cursor.execute("""
            INSERT OR IGNORE INTO StudentWords (student_name, word_id, status)
            VALUES (?, ?, 'learning')
        """, (student_name, word_id))
    
    conn.commit()
    conn.close()

def format_clipboard_output(student_name, step, level, words):
    """Format the output for clipboard."""
    header = f"Currently Learning \u2014 {student_name} \u2014 Step {step} Level {level}"
    word_list = "\n".join([word[1] for word in words])
    return f"{header}\n{word_list}"

def cli_manager(student_name, step, level, words):
    """CLI version of the learning manager."""
    print(f"Select words for {student_name} - Step {step} Level {level}")
    print("Enter word numbers to select (comma separated), or 'all' for all words:")
    
    for i, (word_id, word) in enumerate(words, 1):
        print(f"{i}. {word}")
    
    try:
        selection = input("Selection: ").strip()
        
        if selection.lower() == 'all':
            return [word[0] for word in words]
        
        if selection == "":
            return []
        
        selected_indices = [int(x.strip()) - 1 for x in selection.split(',') if x.strip()]
        selected_word_ids = [words[i][0] for i in selected_indices if 0 <= i < len(words)]
        
        return selected_word_ids
    except (ValueError, IndexError):
        print("Invalid selection.")
        return []

def main():
    parser = argparse.ArgumentParser(description='Manage student learning words')
    parser.add_argument('--student', help='Student name')
    parser.add_argument('--step', type=int, help='Step number (1-28)')
    parser.add_argument('--level', type=int, help='Level number (1-5)')
    args = parser.parse_args()
    
    # Prompt for missing arguments
    if args.student is None:
        args.student = input("Enter student name: ").strip()
    
    if not args.student:
        print("Student name cannot be empty.")
        sys.exit(1)
    
    if args.step is None:
        try:
            args.step = int(input("Enter step (1-28): "))
        except ValueError:
            print("Invalid step number.")
            sys.exit(1)
    
    if args.level is None:
        try:
            args.level = int(input("Enter level (1-5): "))
        except ValueError:
            print("Invalid level number.")
            sys.exit(1)
    
    # Validate inputs
    if not (1 <= args.step <= 28):
        print("Step must be between 1 and 28.")
        sys.exit(1)
    
    if not (1 <= args.level <= 5):
        print("Level must be between 1 and 5.")
        sys.exit(1)
    
    # Get words for step and level
    words = get_words_by_step_level(args.step, args.level)
    
    if not words:
        print("No words found for the specified step and level.")
        return
    
    # Use CLI mode
    selected_word_ids = cli_manager(args.student, args.step, args.level, words)
    
    if selected_word_ids is None:
        print("Operation cancelled.")
        return
    
    if not selected_word_ids:
        print("No words selected.")
        return
    
    # Save selected words
    save_learning_words(args.student, selected_word_ids)
    
    # Get selected words with their text
    selected_words = [(wid, word) for wid, word in words if wid in selected_word_ids]
    
    # Format and copy to clipboard
    output = format_clipboard_output(args.student, args.step, args.level, selected_words)
    pyperclip.copy(output)
    
    # Also print to console
    print(output)
    print("\nCopied to clipboard!")

if __name__ == '__main__':
    main()