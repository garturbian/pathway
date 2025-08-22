# Pathway - Smart Vocabulary Building App

Pathway is a local Windows application for managing smart vocabulary building for multiple students using a 2800-word frequency list.

## Setup

1. **Install Python** (3.10 or higher recommended)
   - Download from [python.org](https://www.python.org/downloads/)
   - Make sure to check "Add Python to PATH" during installation

2. **Install required packages**
   ```bash
   pip install pyperclip
   ```

3. **Prepare the word list**
   - Ensure `words_rank.csv` is in the app root folder
   - The CSV should have columns: Rank, Word

4. **Initialize the database**
   ```bash
   python setup_db.py --csv words_rank.csv
   ```
   This creates `pathway.db` with all words imported and organized into steps and levels.

## Usage

### 1. Fetch Words by Step and Level
Get a specific subgroup of 20 words:
```bash
python subgroup_fetcher.py --step 3 --level 2
```
Or run without arguments to be prompted:
```bash
python subgroup_fetcher.py
```

The words will be copied to your clipboard in this format:
```
Step 3 - Level 2 (Ranks 221–240)
sausage, baloney, pepperoni, ...
```

### 2. Manage Student Learning Words
Select words for a student to learn:
```bash
python learning_manager.py --student "Alice" --step 3 --level 2
```
Or run without arguments to be prompted:
```bash
python learning_manager.py
```

The CLI will display the words and prompt you to select which ones the student doesn't know by entering their numbers (comma separated) or 'all' for all words:

```
Select words for Alice - Step 3 Level 2
Enter word numbers to select (comma separated), or 'all' for all words:
1. build
2. hold
3. service
4. against
5. believe
6. second
7. though
8. yes
9. love
10. increase
11. job
12. plan
13. result
14. away
15. example
16. happen
17. offer
18. young
19. close
20. program
Selection: 1,3,5
```

The selected words will be saved in the database and copied to clipboard:
```
Currently Learning — Alice — Step 3 Level 2
build
service
believe
```

### 3. Retrieve Student Learning Words
Get all words a student is currently learning:
```bash
python retrieve_learning.py --student "Alice"
```
Or run without arguments to be prompted:
```bash
python retrieve_learning.py
```

All learning words will be copied to clipboard, grouped by step and level:
```
Currently Learning — Alice

Step 3 - Level 2 (Ranks 221–240):
sausage, baloney, pepperoni

Step 5 - Level 1 (Ranks 401–420):
kitchen, fix, ahead, ...
```

### 4. Update Student Learning Words
Manage which words a student is currently learning by adding or removing words:

List all words in the database:
```bash
python update_learning.py --list-all
```

Add specific words to a student's learning list:
```bash
python update_learning.py --student "Alice" --add 15 22 38
```

Remove specific words from a student's learning list:
```bash
python update_learning.py --student "Alice" --remove 15 22 38
```

Use interactive mode for easier management:
```bash
python update_learning.py --student "Alice" --interactive
```

Interactive mode provides a menu-driven interface for viewing, adding, and removing words from the learning list.

### 5. Web Interface (NEW)
Pathway now includes a web-based interface for easier management of student learning words, special words, and achievements:

1. **Install web dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Update database schema** (if you haven't already):
   ```bash
   python update_student_progress.py
   ```

3. **Start the web server**:
   ```bash
   python app.py
   ```

4. **Open your browser** and go to `http://localhost:5001`

The web interface provides:
- Interactive management of learning words
- Support for special words (not in the 2800-word database)
- Achievement tracking and rewards system
- Student progress visualization
- Ability to add special words to the learning list (marked with *)
- Automatic checking to prevent adding words that already exist in the 2800-word list
- Track each student's current position on the pathway (step and level)
- Visual feedback for all actions with success/error notifications

## Database Structure

- **Words**: Master list with word, rank, step, and level
  - `id`: Unique identifier
  - `word`: The actual word (unique)
  - `rank`: Position in the frequency list (1-2800)
  - `step`: Group of 100 words (1-28)
  - `level`: Subgroup of 20 words within a step (1-5)
- **StudentWords**: Tracks which words each student is learning or has mastered
  - `id`: Unique identifier
  - `student_name`: Name of the student
  - `word_id`: Reference to the word in the Words table
  - `status`: Either 'learning' or 'mastered'
- **SpecialWords**: Tracks special words not in the 2800-word database
  - `id`: Unique identifier
  - `word`: The special word (unique)
  - `added_date`: When the word was added
  - `notes`: Additional information about the word
- **StudentSpecialWords**: Tracks which special words each student is learning or has mastered
  - `id`: Unique identifier
  - `student_name`: Name of the student
  - `special_word_id`: Reference to the word in the SpecialWords table
  - `status`: Either 'learning' or 'mastered'
  - `added_date`: When the word was added to the student's list
  - `mastered_date`: When the student mastered the word
- **StudentProgress**: Tracks each student's current position on the pathway
  - `id`: Unique identifier
  - `student_name`: Name of the student (unique)
  - `current_step`: Current step (1-28)
  - `current_level`: Current level (1-5)
  - `last_updated`: When the progress was last updated
- **Rewards**: Tracks student achievements
  - `id`: Unique identifier
  - `student_name`: Name of the student
  - `word_id`: Reference to the word in the Words table (if applicable)
  - `special_word_id`: Reference to the word in the SpecialWords table (if applicable)
  - `reward_type`: Type of reward ('word_mastered', 'special_word_mastered', etc.)
  - `reward_date`: When the reward was earned
  - `notes`: Description of the achievement

## How Steps and Levels Work

The 2800 words are organized into:
- **Steps**: 28 groups of 100 words each
- **Levels**: Each step has 5 levels of 20 words each

Formula:
- Step = ((rank - 1) // 100) + 1
- Level = (((rank - 1) % 100) // 20) + 1

## Privacy

All data is stored locally. No internet connection is required or used.