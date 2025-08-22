import sqlite3
import argparse
import sys

def get_learning_words(student_name, db_path='pathway.db'):
    """Get all learning words for a student."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT w.id, w.word, w.step, w.level
        FROM StudentWords sw
        JOIN Words w ON sw.word_id = w.id
        WHERE sw.student_name = ? AND sw.status = 'learning'
        ORDER BY w.step, w.level, w.rank
    """, (student_name,))
    
    words = cursor.fetchall()
    conn.close()
    
    return words

def add_words_to_learning(student_name, word_ids, db_path='pathway.db'):
    """Add words to student's learning list."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for word_id in word_ids:
        cursor.execute("""
            INSERT OR IGNORE INTO StudentWords (student_name, word_id, status)
            VALUES (?, ?, 'learning')
        """, (student_name, word_id))
    
    conn.commit()
    conn.close()

def remove_words_from_learning(student_name, word_ids, db_path='pathway.db'):
    """Remove words from student's learning list."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for word_id in word_ids:
        cursor.execute("""
            DELETE FROM StudentWords
            WHERE student_name = ? AND word_id = ?
        """, (student_name, word_id))
    
    conn.commit()
    conn.close()

def get_word_by_text(word_text, db_path='pathway.db'):
    """Get word ID by its text."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM Words WHERE word = ?", (word_text,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def list_all_words(db_path='pathway.db'):
    """List all words in the database with their IDs."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, word, step, level FROM Words ORDER BY step, level, rank")
    words = cursor.fetchall()
    conn.close()
    
    return words

def format_words_list(words):
    """Format the words list for display."""
    lines = []
    for word_id, word, step, level in words:
        lines.append(f"{word_id:4d}. {word:<15} (Step {step}, Level {level})")
    return "\n".join(lines)

def interactive_mode(student_name, db_path='pathway.db'):
    """Run interactive mode for managing learning words."""
    while True:
        print(f"\n=== Learning Word Manager for {student_name} ===")
        print("1. View current learning words")
        print("2. Add words to learning list")
        print("3. Remove words from learning list")
        print("4. Exit")
        
        choice = input("Select an option (1-4): ").strip()
        
        if choice == '1':
            # View current learning words
            words = get_learning_words(student_name, db_path)
            if words:
                print("\nCurrent learning words:")
                print(format_words_list(words))
            else:
                print("\nNo words currently in learning list.")
                
        elif choice == '2':
            # Add words
            print("\nAdding words to learning list")
            print("Enter word IDs separated by commas, or 'search' to find words:")
            
            action = input("Action: ").strip()
            
            if action.lower() == 'search':
                search_term = input("Enter search term: ").strip()
                if search_term:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT id, word, step, level FROM Words WHERE word LIKE ? ORDER BY word", (f"%{search_term}%",))
                    results = cursor.fetchall()
                    conn.close()
                    
                    if results:
                        print("\nSearch results:")
                        print(format_words_list(results))
                        add_ids_input = input("\nEnter word IDs to add (comma separated): ").strip()
                    else:
                        print("No matching words found.")
                        continue
                else:
                    continue
            else:
                add_ids_input = action
            
            if add_ids_input:
                try:
                    word_ids = [int(x.strip()) for x in add_ids_input.split(',') if x.strip()]
                    add_words_to_learning(student_name, word_ids, db_path)
                    print(f"Added {len(word_ids)} word(s) to learning list.")
                except ValueError:
                    print("Invalid input. Please enter valid word IDs separated by commas.")
                    
        elif choice == '3':
            # Remove words
            words = get_learning_words(student_name, db_path)
            if not words:
                print("\nNo words currently in learning list.")
                continue
                
            print("\nCurrent learning words:")
            print(format_words_list(words))
            
            remove_ids_input = input("\nEnter word IDs to remove (comma separated): ").strip()
            if remove_ids_input:
                try:
                    word_ids = [int(x.strip()) for x in remove_ids_input.split(',') if x.strip()]
                    remove_words_from_learning(student_name, word_ids, db_path)
                    print(f"Removed {len(word_ids)} word(s) from learning list.")
                except ValueError:
                    print("Invalid input. Please enter valid word IDs separated by commas.")
                    
        elif choice == '4':
            print("Goodbye!")
            break
            
        else:
            print("Invalid option. Please select 1-4.")

def main():
    parser = argparse.ArgumentParser(description='Update student learning words')
    parser.add_argument('--student', help='Student name')
    parser.add_argument('--add', nargs='+', help='Word IDs to add to learning list')
    parser.add_argument('--remove', nargs='+', help='Word IDs to remove from learning list')
    parser.add_argument('--list-all', action='store_true', help='List all words in database')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    args = parser.parse_args()
    
    # Prompt for student name if not provided
    if args.student is None and not args.list_all:
        args.student = input("Enter student name: ").strip()
    
    if not args.student and not args.list_all:
        print("Student name cannot be empty.")
        sys.exit(1)
    
    # Handle list-all option
    if args.list_all:
        words = list_all_words()
        print("All words in database:")
        print(format_words_list(words))
        return
    
    # Handle interactive mode
    if args.interactive:
        interactive_mode(args.student)
        return
    
    # Handle add/remove operations
    if args.add:
        try:
            word_ids = [int(x) for x in args.add]
            add_words_to_learning(args.student, word_ids)
            print(f"Added {len(word_ids)} word(s) to {args.student}'s learning list.")
        except ValueError:
            print("Invalid word ID(s). Please provide valid integers.")
            sys.exit(1)
    
    if args.remove:
        try:
            word_ids = [int(x) for x in args.remove]
            remove_words_from_learning(args.student, word_ids)
            print(f"Removed {len(word_ids)} word(s) from {args.student}'s learning list.")
        except ValueError:
            print("Invalid word ID(s). Please provide valid integers.")
            sys.exit(1)
    
    # If no operations specified, show current learning words
    if not args.add and not args.remove:
        words = get_learning_words(args.student)
        if words:
            print(f"\n{args.student}'s current learning words:")
            print(format_words_list(words))
        else:
            print(f"\n{args.student} has no words in learning list.")

if __name__ == '__main__':
    main()