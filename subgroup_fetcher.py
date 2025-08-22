import sqlite3
import pyperclip
import argparse
import sys

def get_words_by_step_level(step, level, db_path='pathway.db'):
    """Get words for a specific step and level."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT word FROM Words 
        WHERE step = ? AND level = ? 
        ORDER BY rank
    """, (step, level))
    
    words = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return words

def format_clipboard_output(step, level, words):
    """Format the output for clipboard."""
    start_rank = ((step - 1) * 100) + ((level - 1) * 20) + 1
    end_rank = start_rank + 19
    header = f"Step {step} - Level {level} (Ranks {start_rank}–{end_rank})"
    word_list = ", ".join(words)
    return f"{header}\n{word_list}"

def main():
    parser = argparse.ArgumentParser(description='Fetch words by step and level')
    parser.add_argument('--step', type=int, help='Step number (1-28)')
    parser.add_argument('--level', type=int, help='Level number (1-5)')
    args = parser.parse_args()
    
    # If arguments not provided, prompt user
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
    
    # Get words
    words = get_words_by_step_level(args.step, args.level)
    
    if not words:
        print("No words found for the specified step and level.")
        return
    
    # Format and copy to clipboard
    output = format_clipboard_output(args.step, args.level, words)
    pyperclip.copy(output)
    
    # Also print to console
    print(output)
    print("\nCopied to clipboard!")

if __name__ == '__main__':
    main()