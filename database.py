import sqlite3
import csv
import json
import os

# 数据库文件路径
DB_NAME = 'database.db'
CSV_FILE = 'questions.csv'
SYSTEM_QUESTION_BANK_ID = 0
SYSTEM_QUESTION_BANK_NAME = "系统默认题库"

def _column_exists(cursor, table_name, column_name):
    """Check whether a column exists on a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row['name'] == column_name for row in cursor.fetchall())

def _rebuild_favorites_table(conn):
    """
    Rebuild the favorites table to introduce the question_bank_id column
    and the updated UNIQUE constraint.
    """
    c = conn.cursor()
    c.execute('ALTER TABLE favorites RENAME TO favorites_old')
    c.execute('''
        CREATE TABLE favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id TEXT NOT NULL,
            question_bank_id INTEGER DEFAULT 0,
            tag TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, question_id, question_bank_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (question_id, question_bank_id) REFERENCES questions(id, question_bank_id)
        )
    ''')
    c.execute('''
        INSERT INTO favorites (id, user_id, question_id, question_bank_id, tag, created_at)
        SELECT id, user_id, question_id, 0, tag, created_at FROM favorites_old
    ''')
    c.execute('DROP TABLE favorites_old')
    conn.commit()

def get_db():
    """
    Create a database connection and configure it to return rows as dictionaries.
    
    Returns:
        sqlite3.Connection: The configured database connection
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def load_questions_to_db(conn, question_bank_id=SYSTEM_QUESTION_BANK_ID, csv_path=None):
    """
    Load questions from a CSV file into the database.
    
    Args:
        conn (sqlite3.Connection): The database connection
        question_bank_id (int): Target question bank ID
        csv_path (str): Optional override for CSV source
    """
    try:
        csv_path = csv_path or CSV_FILE
        if not os.path.exists(csv_path):
            print(f"Warning: {csv_path} file not found. No questions loaded.")
            return

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            c = conn.cursor()
            for row in reader:
                options = {}
                for opt in ['A', 'B', 'C', 'D', 'E']:
                    if row.get(opt) and row[opt].strip():
                        options[opt] = row[opt]
                # 根据现有题型推断详细题型分类
                current_qtype = row["题型"]
                if current_qtype == "单选题":
                    question_type = "单选题"
                elif current_qtype == "多选题":
                    question_type = "多选题"
                elif current_qtype == "判断题":
                    question_type = "判断题"
                elif current_qtype == "填空题":
                    question_type = "填空题"
                else:
                    # 默认为单选题，后续可以根据需要扩展
                    question_type = "单选题"

                c.execute(
                    "INSERT INTO questions (id, stem, answer, difficulty, qtype, category, options, question_type, question_bank_id) VALUES (?,?,?,?,?,?,?,?,?)",
                    (
                        row["题号"],
                        row["题干"],
                        row["答案"],
                        row["难度"],
                        row["题型"],
                        row.get("类别", "未分类"),
                        json.dumps(options, ensure_ascii=False),
                        question_type,
                        question_bank_id,
                    ),
                )
            conn.commit()
            print(f"Successfully loaded questions from {csv_path} into bank {question_bank_id}")
    except Exception as e:
        print(f"Error loading questions: {e}")

def init_db():
    """
    Initialize the database by creating necessary tables if they don't exist.
    Also loads initial question data from CSV if the questions table is empty.
    """
    conn = get_db()
    c = conn.cursor()

    # Questions table for storing question data (created first for FK references)
    c.execute('''CREATE TABLE IF NOT EXISTS questions (
        id TEXT NOT NULL,
        stem TEXT NOT NULL,
        answer TEXT NOT NULL,
        difficulty TEXT,
        qtype TEXT,
        category TEXT,
        options TEXT,
        question_type TEXT,
        question_bank_id INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id, question_bank_id)
    )''')

    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        current_seq_qid TEXT,
        active_question_bank_id INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # History table for tracking user answers
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id TEXT NOT NULL,
        question_bank_id INTEGER DEFAULT 0,
        user_answer TEXT NOT NULL,
        correct INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (question_id, question_bank_id) REFERENCES questions(id, question_bank_id)
    )''')

    # Favorites table for user bookmarks
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id TEXT NOT NULL,
        question_bank_id INTEGER DEFAULT 0,
        tag TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, question_id, question_bank_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (question_id, question_bank_id) REFERENCES questions(id, question_bank_id)
    )''')

    # Exam sessions table for timed mode and exams
    c.execute('''CREATE TABLE IF NOT EXISTS exam_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mode TEXT NOT NULL,
        question_ids TEXT NOT NULL,
        start_time DATETIME NOT NULL,
        duration INTEGER NOT NULL,
        completed BOOLEAN DEFAULT 0,
        score REAL,
        question_bank_id INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # Question banks table for multi-bank support
    c.execute('''CREATE TABLE IF NOT EXISTS question_banks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        is_default BOOLEAN DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    conn.commit()

    # Ensure legacy databases receive new columns / schema updates
    if not _column_exists(c, 'users', 'active_question_bank_id'):
        c.execute('ALTER TABLE users ADD COLUMN active_question_bank_id INTEGER DEFAULT 0')

    if not _column_exists(c, 'history', 'question_bank_id'):
        c.execute('ALTER TABLE history ADD COLUMN question_bank_id INTEGER DEFAULT 0')
        c.execute('UPDATE history SET question_bank_id = 0 WHERE question_bank_id IS NULL')

    if not _column_exists(c, 'favorites', 'question_bank_id'):
        _rebuild_favorites_table(conn)

    # 数据库迁移：为现有数据库添加 question_type 字段
    try:
        c.execute("SELECT question_type FROM questions LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding question_type column to questions table...")
        c.execute("ALTER TABLE questions ADD COLUMN question_type TEXT")
        c.execute("UPDATE questions SET question_type = qtype WHERE question_type IS NULL")
        conn.commit()
        print("Successfully added question_type column")

    # 数据库迁移：为现有数据库添加 question_bank_id 字段
    try:
        c.execute("SELECT question_bank_id FROM questions LIMIT 1")
    except sqlite3.OperationalError:
        print("Adding question_bank_id column to questions table...")
        c.execute("ALTER TABLE questions ADD COLUMN question_bank_id INTEGER DEFAULT 0")
        conn.commit()
        print("Successfully added question_bank_id column")

    # Helpful indexes
    c.execute('CREATE INDEX IF NOT EXISTS idx_questions_bank ON questions(question_bank_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_history_user_bank ON history(user_id, question_bank_id)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_favorites_user_bank ON favorites(user_id, question_bank_id)')
    conn.commit()

    # Load questions from CSV if the table is empty
    c.execute('SELECT COUNT(*) as cnt FROM questions')
    if c.fetchone()['cnt'] == 0:
        load_questions_to_db(conn)

    conn.close()

def fetch_question(qid, question_bank_id=SYSTEM_QUESTION_BANK_ID):
    """
    Fetch a question by ID from the database.

    Args:
        qid (str): The question ID
        question_bank_id (int): The question bank ID, default 0 for system bank

    Returns:
        dict: The question data or None if not found
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM questions WHERE id=? AND question_bank_id=?', (qid, question_bank_id))
    row = c.fetchone()
    conn.close()

    if row:
        return {
            'id': row['id'],
            'stem': row['stem'],
            'answer': row['answer'],
            'difficulty': row['difficulty'],
            'type': row['qtype'],
            'category': row['category'],
            'options': json.loads(row['options']) if row['options'] else {},
            'question_type': row['question_type'] if row['question_type'] else row['qtype'],  # 兼容旧数据
            'question_bank_id': row['question_bank_id']
        }
    return None

def random_question_id(user_id, question_bank_id=SYSTEM_QUESTION_BANK_ID):
    """
    Get a random question ID for a user, excluding questions they've already answered.

    Args:
        user_id (int): The user ID
        question_bank_id (int): The question bank ID, default 0 for system bank

    Returns:
        str: A random question ID or None if all questions have been answered
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id FROM questions
        WHERE id NOT IN (
            SELECT question_id FROM history WHERE user_id=? AND question_bank_id=?
        )
        AND question_bank_id=?
        ORDER BY RANDOM()
        LIMIT 1
    ''', (user_id, question_bank_id, question_bank_id))
    row = c.fetchone()
    conn.close()

    if row:
        return row['id']
    return None

def fetch_random_question_ids(num, question_bank_id=SYSTEM_QUESTION_BANK_ID):
    """
    Fetch multiple random question IDs.

    Args:
        num (int): The number of question IDs to fetch
        question_bank_id (int): The question bank ID, default 0 for system bank

    Returns:
        list: A list of random question IDs
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id FROM questions WHERE question_bank_id=? ORDER BY RANDOM() LIMIT ?',
              (question_bank_id, num))
    rows = c.fetchall()
    conn.close()
    return [r['id'] for r in rows]

def is_favorite(user_id, question_id, question_bank_id=SYSTEM_QUESTION_BANK_ID):
    """
    Check if a question is favorited by a user.

    Args:
        user_id (int): The user ID
        question_id (str): The question ID

    Returns:
        bool: True if favorited, False otherwise
    """
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM favorites WHERE user_id=? AND question_id=? AND question_bank_id=?',
              (user_id, question_id, question_bank_id))
    is_fav = bool(c.fetchone())
    conn.close()
    return is_fav

def create_question_bank(user_id, name, description=""):
    """
    Create a new question bank for a user.

    Args:
        user_id (int): The user ID
        name (str): The name of the question bank
        description (str): Optional description

    Returns:
        int: The ID of the created question bank
    """
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'INSERT INTO question_banks (user_id, name, description) VALUES (?,?,?)',
        (user_id, name, description)
    )
    bank_id = c.lastrowid
    conn.commit()
    conn.close()
    return bank_id

def get_user_question_banks(user_id, include_system=True):
    """
    Get all question banks accessible to a user.

    Args:
        user_id (int): The user ID
        include_system (bool): Whether to include the built-in system bank

    Returns:
        list: List of question bank dictionaries
    """
    conn = get_db()
    c = conn.cursor()
    banks = []

    if include_system:
        c.execute('SELECT COUNT(*) as total FROM questions WHERE question_bank_id=?', (SYSTEM_QUESTION_BANK_ID,))
        total = c.fetchone()['total']
        banks.append({
            'id': SYSTEM_QUESTION_BANK_ID,
            'name': SYSTEM_QUESTION_BANK_NAME,
            'description': '平台预置题库，所有用户可使用',
            'is_default': True,
            'created_at': None,
            'question_count': total,
            'is_system': True
        })

    c.execute('''
        SELECT qb.id, qb.name, qb.description, qb.is_default, qb.created_at,
               (SELECT COUNT(*) FROM questions WHERE question_bank_id = qb.id) as question_count
        FROM question_banks qb
        WHERE qb.user_id=?
        ORDER BY qb.created_at DESC
    ''', (user_id,))
    for row in c.fetchall():
        banks.append({
            'id': row['id'],
            'name': row['name'],
            'description': row['description'],
            'is_default': bool(row['is_default']),
            'created_at': row['created_at'],
            'question_count': row['question_count'],
            'is_system': False
        })
    conn.close()
    return banks

def get_active_question_bank_id(user_id):
    """Return the user's currently active question bank ID."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT active_question_bank_id FROM users WHERE id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if row and row['active_question_bank_id'] is not None:
        return row['active_question_bank_id']
    return SYSTEM_QUESTION_BANK_ID

def user_can_access_bank(user_id, bank_id):
    """Check whether the user can access a question bank."""
    if bank_id == SYSTEM_QUESTION_BANK_ID:
        return True
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM question_banks WHERE id=? AND user_id=?', (bank_id, user_id))
    allowed = c.fetchone() is not None
    conn.close()
    return allowed

def set_active_question_bank_id(user_id, bank_id):
    """Switch the user's active question bank after validating permissions."""
    if not user_can_access_bank(user_id, bank_id):
        raise ValueError("User does not have access to the specified question bank.")
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET active_question_bank_id=?, current_seq_qid=NULL WHERE id=?', (bank_id, user_id))
    conn.commit()
    conn.close()

def get_question_bank_summary(bank_id, user_id=None):
    """Return metadata about a question bank (name, counts, timestamps)."""
    conn = get_db()
    c = conn.cursor()
    summary = None
    if bank_id == SYSTEM_QUESTION_BANK_ID:
        c.execute('SELECT COUNT(*) as total, MAX(created_at) as last_updated FROM questions WHERE question_bank_id=?',
                  (bank_id,))
        stats = c.fetchone()
        summary = {
            'id': SYSTEM_QUESTION_BANK_ID,
            'name': SYSTEM_QUESTION_BANK_NAME,
            'description': '平台内置题库，所有用户可用',
            'question_count': stats['total'] if stats else 0,
            'last_updated': stats['last_updated'],
            'created_at': None,
            'is_system': True
        }
    else:
        c.execute('SELECT * FROM question_banks WHERE id=?', (bank_id,))
        row = c.fetchone()
        if row and (user_id is None or row['user_id'] == user_id):
            c.execute('SELECT COUNT(*) as total, MAX(created_at) as last_updated FROM questions WHERE question_bank_id=?',
                      (bank_id,))
            stats = c.fetchone()
            summary = {
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'question_count': stats['total'] if stats else 0,
                'last_updated': stats['last_updated'],
                'created_at': row['created_at'],
                'is_system': False
            }
    conn.close()
    return summary

def get_question_bank_preview(bank_id, limit=10):
    """Return a lightweight preview of questions inside a bank."""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, stem, difficulty, qtype, category, answer, options
        FROM questions
        WHERE question_bank_id=?
        ORDER BY CAST(id AS INTEGER) ASC
        LIMIT ?
    ''', (bank_id, limit))
    rows = c.fetchall()
    conn.close()
    preview = []
    for row in rows:
        preview.append({
            'id': row['id'],
            'stem': row['stem'],
            'difficulty': row['difficulty'],
            'qtype': row['qtype'],
            'category': row['category'],
            'answer': row['answer'],
            'options': json.loads(row['options']) if row['options'] else {}
        })
    return preview

def delete_question_bank(user_id, bank_id):
    """Delete a custom question bank and its associated data."""
    if bank_id == SYSTEM_QUESTION_BANK_ID:
        raise ValueError("系统默认题库不可删除")
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT 1 FROM question_banks WHERE id=? AND user_id=?', (bank_id, user_id))
    if not c.fetchone():
        conn.close()
        return False

    c.execute('DELETE FROM history WHERE question_bank_id=?', (bank_id,))
    c.execute('DELETE FROM favorites WHERE question_bank_id=?', (bank_id,))
    c.execute('DELETE FROM exam_sessions WHERE question_bank_id=?', (bank_id,))
    c.execute('DELETE FROM questions WHERE question_bank_id=?', (bank_id,))
    c.execute('DELETE FROM question_banks WHERE id=?', (bank_id,))
    c.execute('UPDATE users SET active_question_bank_id=?, current_seq_qid=NULL WHERE id=? AND active_question_bank_id=?',
              (SYSTEM_QUESTION_BANK_ID, user_id, bank_id))
    conn.commit()
    conn.close()
    return True
