import sqlite3
import csv
import json
import os

# 数据库文件路径
DB_NAME = 'database.db'
CSV_FILE = 'questions.csv'

def get_db():
    """
    Create a database connection and configure it to return rows as dictionaries.
    
    Returns:
        sqlite3.Connection: The configured database connection
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def load_questions_to_db(conn):
    """
    Load questions from a CSV file into the database.
    
    Args:
        conn (sqlite3.Connection): The database connection
    """
    try:
        if not os.path.exists(CSV_FILE):
            print(f"Warning: {CSV_FILE} file not found. No questions loaded.")
            return

        with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
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
                        0,  # 系统默认题库
                    ),
                )
            conn.commit()
            print(f"Successfully loaded questions from {CSV_FILE}")
    except Exception as e:
        print(f"Error loading questions: {e}")

def init_db():
    """
    Initialize the database by creating necessary tables if they don't exist.
    Also loads initial question data from CSV if the questions table is empty.
    """
    conn = get_db()
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        current_seq_qid TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # History table for tracking user answers
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id TEXT NOT NULL,
        user_answer TEXT NOT NULL,
        correct INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    # Questions table for storing question data
    c.execute('''CREATE TABLE IF NOT EXISTS questions (
        id TEXT NOT NULL,
        stem TEXT NOT NULL,
        answer TEXT NOT NULL,
        difficulty TEXT,
        qtype TEXT,
        category TEXT,
        options TEXT, -- JSON stored options
        question_type TEXT, -- 详细题型分类：单选题、多选题、判断题、填空题等
        question_bank_id INTEGER DEFAULT 0, -- 题库ID，0表示系统默认题库
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id, question_bank_id)
    )''')
    
    # Favorites table for user bookmarks
    c.execute('''CREATE TABLE IF NOT EXISTS favorites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        question_id TEXT NOT NULL,
        tag TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, question_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (question_id) REFERENCES questions(id)
    )''')
    
    # Exam sessions table for timed mode and exams
    c.execute('''CREATE TABLE IF NOT EXISTS exam_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mode TEXT NOT NULL, -- 'exam' or 'timed'
        question_ids TEXT NOT NULL, -- JSON list
        start_time DATETIME NOT NULL,
        duration INTEGER NOT NULL, -- seconds
        completed BOOLEAN DEFAULT 0,
        score REAL,
        question_bank_id INTEGER DEFAULT 0, -- 使用的题库ID
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')

    # Question banks table for multi-bank support
    c.execute('''CREATE TABLE IF NOT EXISTS question_banks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        is_default BOOLEAN DEFAULT 0, -- 是否为默认题库
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    
    conn.commit()

    # 数据库迁移：为现有数据库添加 question_type 字段
    try:
        c.execute("SELECT question_type FROM questions LIMIT 1")
    except sqlite3.OperationalError:
        # 字段不存在，需要添加
        print("Adding question_type column to questions table...")
        c.execute("ALTER TABLE questions ADD COLUMN question_type TEXT")

        # 为现有数据设置默认值
        c.execute("UPDATE questions SET question_type = qtype WHERE question_type IS NULL")
        conn.commit()
        print("Successfully added question_type column")

    # 数据库迁移：为现有数据库添加 question_bank_id 字段
    try:
        c.execute("SELECT question_bank_id FROM questions LIMIT 1")
    except sqlite3.OperationalError:
        # 字段不存在，需要添加
        print("Adding question_bank_id column to questions table...")
        c.execute("ALTER TABLE questions ADD COLUMN question_bank_id INTEGER DEFAULT 0")
        conn.commit()
        print("Successfully added question_bank_id column")

    # Load questions from CSV if the table is empty
    c.execute('SELECT COUNT(*) as cnt FROM questions')
    if c.fetchone()['cnt'] == 0:
        load_questions_to_db(conn)
    
    conn.close()

def fetch_question(qid, question_bank_id=0):
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
            'options': json.loads(row['options']),
            'question_type': row['question_type'] if row['question_type'] else row['qtype'],  # 兼容旧数据
            'question_bank_id': row['question_bank_id']
        }
    return None

def random_question_id(user_id, question_bank_id=0):
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
            SELECT question_id FROM history WHERE user_id=?
        )
        AND question_bank_id=?
        ORDER BY RANDOM()
        LIMIT 1
    ''', (user_id, question_bank_id))
    row = c.fetchone()
    conn.close()

    if row:
        return row['id']
    return None

def fetch_random_question_ids(num, question_bank_id=0):
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

def is_favorite(user_id, question_id):
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
    c.execute('SELECT 1 FROM favorites WHERE user_id=? AND question_id=?',
              (user_id, question_id))
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

def get_user_question_banks(user_id):
    """
    Get all question banks for a user.

    Args:
        user_id (int): The user ID

    Returns:
        list: List of question bank dictionaries
    """
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'SELECT id, name, description, is_default, created_at FROM question_banks WHERE user_id=? ORDER BY created_at DESC',
        (user_id,)
    )
    banks = []
    for row in c.fetchall():
        banks.append({
            'id': row['id'],
            'name': row['name'],
            'description': row['description'],
            'is_default': bool(row['is_default']),
            'created_at': row['created_at']
        })
    conn.close()
    return banks