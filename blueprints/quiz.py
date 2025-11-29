import json
import random
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, render_template, session, redirect, url_for, flash, jsonify
from database import (
    get_db,
    fetch_question,
    random_question_id,
    is_favorite,
    fetch_random_question_ids,
    get_active_question_bank_id,
    get_active_ai_provider,
    SYSTEM_QUESTION_BANK_ID,
    parse_fill_answers,
)
from .auth import login_required, get_user_id

bp = Blueprint('quiz', __name__)

def validate_answer_by_type(question_type, user_answer, correct_answer):
    """
    根据题型验证用户答案

    Args:
        question_type (str): 题型（单选题、多选题、判断题、填空题）
        user_answer (str): 用户答案
        correct_answer (str): 正确答案

    Returns:
        int: 1表示正确，0表示错误
    """
    if question_type == "单选题":
        return int(user_answer == correct_answer)
    elif question_type == "多选题":
        # 多选题需要排序后比较
        return int("".join(sorted(user_answer)) == "".join(sorted(correct_answer)))
    elif question_type == "判断题":
        # 判断题直接比较文本
        return int(user_answer == correct_answer)
    elif question_type == "填空题":
        user_parts = [part.strip().lower() for part in parse_fill_answers(user_answer)]
        correct_parts = [part.strip().lower() for part in parse_fill_answers(correct_answer)]
        if not correct_parts:
            return 0
        if len(user_parts) != len(correct_parts):
            return 0
        return int(all(u == c for u, c in zip(user_parts, correct_parts)))
    else:
        # 默认使用单选题验证逻辑
        return int(user_answer == correct_answer)


def serialize_user_answer(question_type, answers):
    """Format posted answers into the string stored in history."""
    if not answers:
        return ""
    if question_type == "填空题":
        normalized = [ans.strip() for ans in answers]
        return "".join(f"({value})" for value in normalized)
    return "".join(answers)


def build_ai_context(question, user_answer, has_result, has_provider):
    """组装前端 AI 浮窗所需的上下文。"""
    if not question:
        return {
            'enabled': False,
            'hasActiveProvider': has_provider,
            'questionId': None,
            'questionBankId': SYSTEM_QUESTION_BANK_ID,
            'hasSubmission': has_result,
            'userAnswer': user_answer or '',
            'questionStem': ''
        }

    return {
        'enabled': has_provider,
        'hasActiveProvider': has_provider,
        'questionId': question['id'],
        'questionBankId': question.get('question_bank_id', SYSTEM_QUESTION_BANK_ID),
        'hasSubmission': bool(has_result),
        'userAnswer': user_answer or '',
        'questionStem': question.get('stem', ''),
        'questionType': question.get('question_type') or question.get('type')
    }

# --- Random & Single Question ---

@bp.route('/random', methods=['GET'])
@login_required
def random_question():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    has_ai_provider = bool(get_active_ai_provider(user_id))
    qid = random_question_id(user_id, question_bank_id)
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) as total FROM questions WHERE question_bank_id=?', (question_bank_id,))
    total = c.fetchone()['total']
    c.execute('SELECT COUNT(DISTINCT question_id) as answered FROM history WHERE user_id=? AND question_bank_id=?', (user_id, question_bank_id))
    answered = c.fetchone()['answered']
    conn.close()
    
    if not qid:
        flash("您已完成所有题目！可以重置历史以重新开始。", "info")
        return render_template(
            'question.html',
            question=None,
            answered=answered,
            total=total,
            user_answer='',
            fill_user_answers=[],
            result_correct=None,
            ai_context=build_ai_context(None, '', False, has_ai_provider)
        )
        
    q = fetch_question(qid, question_bank_id)
    is_fav = is_favorite(user_id, qid, question_bank_id)
    user_answer_value = ''
    fill_user_answers = []
    if q and q.get('question_type', q.get('type')) == '填空题':
        fill_user_answers = parse_fill_answers(user_answer_value)
    
    return render_template(
        'question.html',
        question=q,
        answered=answered,
        total=total,
        is_favorite=is_fav,
        user_answer=user_answer_value,
        fill_user_answers=fill_user_answers,
        result_correct=None,
        ai_context=build_ai_context(q, user_answer_value, False, has_ai_provider)
    )

@bp.route('/question/<qid>', methods=['GET', 'POST'])
@login_required
def show_question(qid):
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    q = fetch_question(qid, question_bank_id)
    has_ai_provider = bool(get_active_ai_provider(user_id))
    user_answer_str = ""
    result_correct = None
    
    if q is None:
        flash("题目不存在", "error")
        return redirect(url_for('main.index'))
    
    question_type = q.get('question_type', q['type'])
    fill_user_answers = []

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (qid, user_id))
    conn.commit()

    if request.method == 'POST':
        user_answer = request.form.getlist('answer')
        user_answer_str = serialize_user_answer(question_type, user_answer)
        if question_type == '填空题':
            fill_user_answers = parse_fill_answers(user_answer_str)

        # 使用新的验证函数
        correct = validate_answer_by_type(question_type, user_answer_str, q['answer'])
        result_correct = bool(correct)

        c.execute(
            'INSERT INTO history (user_id, question_id, question_bank_id, user_answer, correct) VALUES (?,?,?,?,?)',
            (user_id, qid, question_bank_id, user_answer_str, correct)
        )
        conn.commit()

        c.execute('SELECT COUNT(*) AS total FROM questions WHERE question_bank_id=?', (question_bank_id,))
        total = c.fetchone()['total']
        c.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id=? AND question_bank_id=?', (user_id, question_bank_id))
        answered = c.fetchone()['answered']
        conn.close()

        result_msg = "回答正确" if correct else f"回答错误，正确答案：{q['answer']}"
        flash(result_msg, "success" if correct else "error")
        
        is_fav = is_favorite(user_id, qid, question_bank_id)
        
        return render_template(
            'question.html',
            question=q,
            result_msg=result_msg,
            answered=answered,
            total=total,
            is_favorite=is_fav,
            user_answer=user_answer_str,
            fill_user_answers=fill_user_answers,
            result_correct=result_correct,
            ai_context=build_ai_context(q, user_answer_str, True, has_ai_provider)
        )

    c.execute('SELECT COUNT(*) AS total FROM questions WHERE question_bank_id=?', (question_bank_id,))
    total = c.fetchone()['total']
    c.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id=? AND question_bank_id=?', (user_id, question_bank_id))
    answered = c.fetchone()['answered']
    conn.close()
    
    is_fav = is_favorite(user_id, qid, question_bank_id)

    return render_template(
        'question.html',
        question=q,
        answered=answered,
        total=total,
        is_favorite=is_fav,
        user_answer=user_answer_str,
        fill_user_answers=fill_user_answers,
        result_correct=result_correct,
        ai_context=build_ai_context(q, user_answer_str, False, has_ai_provider)
    )

# --- Search & Filter ---

@bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    query = request.form.get('query', '')
    results = []
    
    if query:
        conn = get_db()
        c = conn.cursor()
        like_term = f'%{query}%'
        c.execute("SELECT * FROM questions WHERE question_bank_id=? AND (stem LIKE ? OR id LIKE ?)",
                  (question_bank_id, like_term, like_term))
        rows = c.fetchall()
        conn.close()
        
        for row in rows:
            results.append({'id': row['id'], 'stem': row['stem']})
    
    return render_template('search.html', query=query, results=results)

@bp.route('/browse')
@login_required
def browse_questions():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    page = request.args.get('page', 1, type=int)
    question_type = request.args.get('type', '')
    search_query = request.args.get('search', '')
    difficulty_filters = request.args.getlist('difficulty')
    category_filters = request.args.getlist('category')
    per_page = 20

    conn = get_db()
    c = conn.cursor()

    where_conditions = ['question_bank_id = ?']
    params = [question_bank_id]

    if question_type and question_type != 'all':
        where_conditions.append('qtype = ?')
        params.append(question_type)

    if search_query:
        where_conditions.append('(stem LIKE ? OR id LIKE ?)')
        params.extend(['%' + search_query + '%', '%' + search_query + '%'])

    # 难度筛选 - 多选支持
    if difficulty_filters and 'all' not in difficulty_filters:
        placeholders = ','.join(['?'] * len(difficulty_filters))
        where_conditions.append(f'difficulty IN ({placeholders})')
        params.extend(difficulty_filters)

    # 分类筛选 - 多选支持
    if category_filters and 'all' not in category_filters:
        placeholders = ','.join(['?'] * len(category_filters))
        where_conditions.append(f'category IN ({placeholders})')
        params.extend(category_filters)

    where_clause = ' WHERE ' + ' AND '.join(where_conditions) if where_conditions else ''
    
    c.execute(f'SELECT COUNT(*) as total FROM questions{where_clause}', params)
    total = c.fetchone()['total']
    
    offset = (page - 1) * per_page
    query_params = params + [per_page, offset]
    c.execute(f'''
        SELECT id, stem, answer, difficulty, qtype, category, options 
        FROM questions 
        {where_clause}
        ORDER BY CAST(id AS INTEGER) ASC 
        LIMIT ? OFFSET ?
    ''', query_params)
    
    rows = c.fetchall()
    questions = []
    
    for row in rows:
        question_data = {
            'id': row['id'],
            'stem': row['stem'],
            'answer': row['answer'],
            'difficulty': row['difficulty'],
            'type': row['qtype'],
            'category': row['category'],
            'options': json.loads(row['options']) if row['options'] else {}
        }
        c.execute('SELECT 1 FROM favorites WHERE user_id=? AND question_id=? AND question_bank_id=?', 
                  (user_id, row['id'], question_bank_id))
        question_data['is_favorite'] = bool(c.fetchone())
        questions.append(question_data)
    
    c.execute('''
        SELECT DISTINCT qtype FROM questions
        WHERE question_bank_id=? AND qtype IS NOT NULL AND qtype != ""
        ORDER BY qtype
    ''', (question_bank_id,))
    available_types = [r['qtype'] for r in c.fetchall()]

    c.execute('''
        SELECT DISTINCT difficulty FROM questions
        WHERE question_bank_id=? AND difficulty IS NOT NULL AND difficulty != ""
        ORDER BY difficulty
    ''', (question_bank_id,))
    available_difficulties = [r['difficulty'] for r in c.fetchall()]

    c.execute('''
        SELECT DISTINCT category FROM questions
        WHERE question_bank_id=? AND category IS NOT NULL AND category != ""
        ORDER BY category
    ''', (question_bank_id,))
    available_categories = [r['category'] for r in c.fetchall()]
    conn.close()

    total_pages = (total + per_page - 1) // per_page
    has_prev = page > 1
    has_next = page < total_pages
    
    return render_template('browse.html',
                           questions=questions,
                           total=total,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           has_prev=has_prev,
                           has_next=has_next,
                           current_type=question_type,
                           current_search=search_query,
                           current_difficulties=difficulty_filters,
                           current_categories=category_filters,
                           available_types=available_types,
                           available_difficulties=available_difficulties,
                           available_categories=available_categories)

@bp.route('/filter', methods=['GET', 'POST'])
@login_required
def filter_questions():
    conn = get_db()
    c = conn.cursor()
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    
    c.execute('SELECT DISTINCT category FROM questions WHERE question_bank_id=? AND category IS NOT NULL AND category != ""',
              (question_bank_id,))
    categories = [r['category'] for r in c.fetchall()]
    
    c.execute('SELECT DISTINCT difficulty FROM questions WHERE difficulty IS NOT NULL AND difficulty != "" AND question_bank_id=?',
              (question_bank_id,))
    difficulties = [r['difficulty'] for r in c.fetchall()]

    selected_category = ''
    selected_difficulty = ''
    results = []
    
    if request.method == 'POST':
        selected_category = request.form.get('category', '')
        selected_difficulty = request.form.get('difficulty', '')
        
        sql = "SELECT id, stem FROM questions WHERE question_bank_id=?"
        params = [question_bank_id]
        if selected_category:
            sql += " AND category=?"
            params.append(selected_category)
        if selected_difficulty:
            sql += " AND difficulty=?"
            params.append(selected_difficulty)
            
        c.execute(sql, params)
        rows = c.fetchall()
        for row in rows:
            results.append({'id': row['id'], 'stem': row['stem']})

    conn.close()
    return render_template('filter.html', 
                          categories=categories, 
                          difficulties=difficulties,
                          selected_category=selected_category,
                          selected_difficulty=selected_difficulty,
                          results=results)

# --- Study / Memorize Mode ---

@bp.route('/study')
@login_required
def study_mode():
    """Display a cram-friendly page that shows answers directly."""
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    order_mode = request.args.get('order', 'sequential')
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = request.args.get('per_page', 10, type=int)
    allowed_sizes = [10, 20, 30, 50]
    if per_page not in allowed_sizes:
        per_page = 10

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) AS total FROM questions WHERE question_bank_id=?', (question_bank_id,))
    total = c.fetchone()['total'] or 0

    total_pages = max((total + per_page - 1) // per_page, 1) if total else 0
    if total_pages and page > total_pages:
        page = total_pages

    shuffle_seed = request.args.get('shuffle_seed', '')
    questions = []

    if total:
        if order_mode == 'random':
            if not shuffle_seed:
                shuffle_seed = secrets.token_hex(4)
            c.execute('''
                SELECT id, stem, answer, difficulty, qtype, category, options, question_type
                FROM questions
                WHERE question_bank_id=?
            ''', (question_bank_id,))
            rows = list(c.fetchall())
            rng = random.Random(shuffle_seed)
            rng.shuffle(rows)
            start = (page - 1) * per_page
            end = start + per_page
            rows = rows[start:end]
        else:
            order_mode = 'sequential'
            offset = (page - 1) * per_page
            c.execute('''
                SELECT id, stem, answer, difficulty, qtype, category, options, question_type
                FROM questions
                WHERE question_bank_id=?
                ORDER BY CAST(id AS INTEGER) ASC
                LIMIT ? OFFSET ?
            ''', (question_bank_id, per_page, offset))
            rows = c.fetchall()

        for row in rows:
            question_type = row['question_type'] or row['qtype']
            options = json.loads(row['options']) if row['options'] else {}
            questions.append({
                'id': row['id'],
                'stem': row['stem'],
                'answer': row['answer'],
                'difficulty': row['difficulty'],
                'type': row['qtype'],
                'question_type': question_type,
                'category': row['category'],
                'options': options,
                'fill_answers': parse_fill_answers(row['answer']) if question_type == '填空题' else []
            })
    conn.close()

    display_start = ((page - 1) * per_page + 1) if total else 0
    display_end = min(page * per_page, total) if total else 0

    pagination_params = {
        'order': order_mode if order_mode in {'sequential', 'random'} else 'sequential',
        'per_page': per_page,
    }
    if pagination_params['order'] == 'random' and shuffle_seed:
        pagination_params['shuffle_seed'] = shuffle_seed

    mode_label = '乱序背题' if pagination_params['order'] == 'random' else '顺序背题'

    template_data = {
        'questions': questions,
        'order_mode': pagination_params['order'],
        'per_page': per_page,
        'per_page_options': allowed_sizes,
        'page': page if total else 1,
        'total': total,
        'total_pages': total_pages,
        'display_start': display_start,
        'display_end': display_end,
        'shuffle_seed': shuffle_seed if order_mode == 'random' else '',
        'pagination_params': pagination_params,
        'mode_label': mode_label,
    }
    return render_template('study_mode.html', **template_data)

# --- Sequential Mode ---

@bp.route('/sequential_start')
@login_required
def sequential_start():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT current_seq_qid FROM users WHERE id=?', (user_id,))
    user_data = c.fetchone()
    
    if user_data and user_data['current_seq_qid']:
        potential_qid = user_data['current_seq_qid']
        current_question = fetch_question(potential_qid, question_bank_id)
        current_qid = potential_qid if current_question else None
    else:
        current_qid = None
    
    if not current_qid:
        c.execute('''
            SELECT id FROM questions
            WHERE question_bank_id = ?
              AND id NOT IN (
                  SELECT question_id FROM history WHERE user_id = ? AND question_bank_id = ?
              )
            ORDER BY CAST(id AS INTEGER) ASC LIMIT 1
        ''', (question_bank_id, user_id, question_bank_id))
        row = c.fetchone()
        
        if row is None:
            c.execute('SELECT id FROM questions WHERE question_bank_id=? ORDER BY CAST(id AS INTEGER) ASC LIMIT 1',
                      (question_bank_id,))
            row = c.fetchone()
            if row is None:
                conn.close()
                flash("题库中没有题目！", "error")
                return redirect(url_for('main.index'))
            current_qid = row['id']
            flash("所有题目已完成，从第一题重新开始。", "info")
        else:
            current_qid = row['id']
        
        c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (current_qid, user_id))
        conn.commit()
    
    conn.close()
    return redirect(url_for('quiz.show_sequential_question', qid=current_qid))

@bp.route('/sequential/<qid>', methods=['GET', 'POST'])
@login_required
def show_sequential_question(qid):
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    q = fetch_question(qid, question_bank_id)
    has_ai_provider = bool(get_active_ai_provider(user_id))
    
    if q is None:
        flash("题目不存在", "error")
        return redirect(url_for('main.index'))
    
    question_type = q.get('question_type', q['type'])

    next_qid = None
    result_msg = None
    user_answer_str = ""
    fill_user_answers = []
    result_correct = None
    
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (qid, user_id))
    conn.commit()
    
    if request.method == 'POST':
        user_answer = request.form.getlist('answer')
        user_answer_str = serialize_user_answer(question_type, user_answer)
        if question_type == '填空题':
            fill_user_answers = parse_fill_answers(user_answer_str)

        # 使用新的验证函数
        correct = validate_answer_by_type(question_type, user_answer_str, q['answer'])
        result_correct = bool(correct)
        
        c.execute('INSERT INTO history (user_id, question_id, question_bank_id, user_answer, correct) VALUES (?,?,?,?,?)',
                  (user_id, qid, question_bank_id, user_answer_str, correct))
        
        c.execute('''
            SELECT id FROM questions
            WHERE CAST(id AS INTEGER) > ?
              AND question_bank_id = ?
              AND id NOT IN (SELECT question_id FROM history WHERE user_id = ? AND question_bank_id = ?)
            ORDER BY CAST(id AS INTEGER) ASC LIMIT 1
        ''', (int(qid), question_bank_id, user_id, question_bank_id))
        
        row = c.fetchone()
        if row:
            next_qid = row['id']
            c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (next_qid, user_id))
        else:
            c.execute('''
                SELECT id FROM questions
                WHERE question_bank_id = ?
                  AND id NOT IN (SELECT question_id FROM history WHERE user_id = ? AND question_bank_id = ?)
                ORDER BY CAST(id AS INTEGER) ASC LIMIT 1
            ''', (question_bank_id, user_id, question_bank_id))
            row = c.fetchone()
            if row:
                next_qid = row['id']
                c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (next_qid, user_id))
            else:
                c.execute('SELECT id FROM questions WHERE question_bank_id=? ORDER BY CAST(id AS INTEGER) ASC LIMIT 1',
                          (question_bank_id,))
                row = c.fetchone()
                if row:
                    next_qid = row['id']
                    c.execute('UPDATE users SET current_seq_qid = ? WHERE id = ?', (next_qid, user_id))
                    flash("所有题目已完成，从第一题重新开始。", "info")
                else:
                    c.execute('UPDATE users SET current_seq_qid = NULL WHERE id = ?', (user_id,))
            
        result_msg = "回答正确！" if correct else f"回答错误，正确答案：{q['answer']}"
        flash(result_msg, "success" if correct else "error")
    
    c.execute('SELECT COUNT(*) AS total FROM questions WHERE question_bank_id=?', (question_bank_id,))
    total = c.fetchone()['total']
    c.execute('SELECT COUNT(DISTINCT question_id) AS answered FROM history WHERE user_id = ? AND question_bank_id=?',
              (user_id, question_bank_id))
    answered = c.fetchone()['answered']
    conn.commit()
    conn.close()
    
    is_fav = is_favorite(user_id, qid, question_bank_id)
    
    return render_template(
        'question.html',
        question=q,
        result_msg=result_msg,
        next_qid=next_qid,
        sequential_mode=True,
        user_answer=user_answer_str,
        fill_user_answers=fill_user_answers,
        answered=answered,
        total=total,
        is_favorite=is_fav,
        result_correct=result_correct,
        ai_context=build_ai_context(q, user_answer_str, bool(result_msg), has_ai_provider)
    )

# --- Modes & Exams ---

@bp.route('/modes')
@login_required
def modes():
    return render_template('index.html', mode_select=True, current_year=datetime.now().year)

@bp.route('/start_timed_mode', methods=['POST'])
@login_required
def start_timed_mode():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    question_count = int(request.form.get('question_count', 5))
    duration_minutes = int(request.form.get('duration', 10))
    
    question_ids = fetch_random_question_ids(question_count, question_bank_id)
    start_time = datetime.now()
    duration = duration_minutes * 60
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO exam_sessions 
            (user_id, mode, question_ids, start_time, duration, question_bank_id) 
            VALUES (?,?,?,?,?,?)
        ''', (user_id, 'timed', json.dumps(question_ids), start_time, duration, question_bank_id))
        
        exam_id = c.lastrowid
        conn.commit()
        session['current_exam_id'] = exam_id
        return redirect(url_for('quiz.timed_mode'))
    except Exception as e:
        flash(f"启动定时模式失败: {str(e)}", "error")
        return redirect(url_for('main.index'))
    finally:
        conn.close()

@bp.route('/timed_mode')
@login_required
def timed_mode():
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        flash("未启动定时模式", "error")
        return redirect(url_for('main.index'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = c.fetchone()
    conn.close()
    
    if not exam:
        flash("无法找到考试会话", "error")
        return redirect(url_for('main.index'))
    
    question_bank_id = exam['question_bank_id'] if exam else get_active_question_bank_id(user_id)
    question_bank_id = exam['question_bank_id'] if exam else get_active_question_bank_id(user_id)
    question_bank_id = exam['question_bank_id'] if exam else get_active_question_bank_id(user_id)
    question_ids = json.loads(exam['question_ids'])
    start_time = datetime.strptime(exam['start_time'], '%Y-%m-%d %H:%M:%S.%f')
    end_time = start_time + timedelta(seconds=exam['duration'])
    
    remaining = (end_time - datetime.now()).total_seconds()
    if remaining <= 0:
        return redirect(url_for('quiz.submit_timed_mode'))
    
    questions_list = [fetch_question(qid, question_bank_id) for qid in question_ids]
    return render_template('timed_mode.html', questions=questions_list, remaining=remaining)

@bp.route('/submit_timed_mode', methods=['POST', 'GET'])
@login_required
def submit_timed_mode():
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        flash("没有正在进行的定时模式", "error")
        return redirect(url_for('main.index'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = c.fetchone()
    
    if not exam:
        conn.close()
        flash("无法找到考试会话", "error")
        return redirect(url_for('main.index'))
    
    question_ids = json.loads(exam['question_ids'])
    question_bank_id = exam['question_bank_id'] if exam else get_active_question_bank_id(user_id)
    correct_count = 0
    total = len(question_ids)
    
    for qid in question_ids:
        user_answer = request.form.getlist(f'answer_{qid}')
        q = fetch_question(qid, question_bank_id)
        if not q: continue
        question_type = q.get('question_type', q['type'])
        user_answer_str = serialize_user_answer(question_type, user_answer)

        # 使用新的验证函数
        correct = validate_answer_by_type(question_type, user_answer_str, q['answer'])
        if correct: correct_count += 1
        c.execute('INSERT INTO history (user_id, question_id, question_bank_id, user_answer, correct) VALUES (?,?,?,?,?)',
                  (user_id, qid, question_bank_id, user_answer_str, correct))
    
    score = (correct_count / total * 100) if total > 0 else 0
    c.execute('UPDATE exam_sessions SET completed=1, score=? WHERE id=?', (score, exam_id))
    conn.commit()
    conn.close()
    
    session.pop('current_exam_id', None)
    flash(f"定时模式结束！正确率：{correct_count}/{total} = {score:.2f}%", 
          "success" if score >= 60 else "error")
    return redirect(url_for('user.statistics'))

@bp.route('/start_exam', methods=['POST'])
@login_required
def start_exam():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    question_count = int(request.form.get('question_count', 10))
    question_ids = fetch_random_question_ids(question_count, question_bank_id)
    start_time = datetime.now()
    duration = 0
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO exam_sessions 
            (user_id, mode, question_ids, start_time, duration, question_bank_id) 
            VALUES (?,?,?,?,?,?)
        ''', (user_id, 'exam', json.dumps(question_ids), start_time, duration, question_bank_id))
        
        exam_id = c.lastrowid
        conn.commit()
        session['current_exam_id'] = exam_id
        return redirect(url_for('quiz.exam'))
    except Exception as e:
        flash(f"启动模拟考试失败: {str(e)}", "error")
        return redirect(url_for('main.index'))
    finally:
        conn.close()

@bp.route('/exam')
@login_required
def exam():
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    # 检查1：是否有 exam_id
    if not exam_id:
        flash("未启动考试模式", "error")
        return redirect(url_for('main.index'))
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam_data = c.fetchone() # 建议改名以免和函数名混淆，不过 Python 允许这样
    conn.close()
    
    # 检查2：数据库里有没有这个考试
    if not exam_data:
        flash("无法找到考试", "error")
        return redirect(url_for('main.index'))
    
    # === 关键点：以下代码必须和上面的 if 保持同级缩进，不能缩进进去 ===
    question_bank_id = exam_data['question_bank_id']
    question_ids = json.loads(exam_data['question_ids'])
    questions_list = [fetch_question(qid, question_bank_id) for qid in question_ids]
    
    # 必须有这个 return
    return render_template('exam.html', questions=questions_list)
@bp.route('/submit_exam', methods=['POST'])
@login_required
def submit_exam():
    user_id = get_user_id()
    exam_id = session.get('current_exam_id')
    
    if not exam_id:
        return jsonify({"success": False, "msg": "没有正在进行的考试"}), 400
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM exam_sessions WHERE id=? AND user_id=?', (exam_id, user_id))
    exam = c.fetchone()
    
    if not exam:
        conn.close()
        return jsonify({"success": False, "msg": "无法找到考试"}), 404
    
    question_ids = json.loads(exam['question_ids'])
    question_bank_id = exam['question_bank_id'] if exam else get_active_question_bank_id(user_id)
    correct_count = 0
    total = len(question_ids)
    question_results = []
    
    for qid in question_ids:
        user_answer = request.form.getlist(f'answer_{qid}')
        q = fetch_question(qid, question_bank_id)
        if not q: continue
        question_type = q.get('question_type', q['type'])
        user_answer_str = serialize_user_answer(question_type, user_answer)

        # 使用新的验证函数
        correct = validate_answer_by_type(question_type, user_answer_str, q['answer'])
        if correct: correct_count += 1
        
        c.execute('INSERT INTO history (user_id, question_id, question_bank_id, user_answer, correct) VALUES (?,?,?,?,?)',
                  (user_id, qid, question_bank_id, user_answer_str, correct))
        
        question_results.append({
            "id": qid,
            "stem": q['stem'],
            "user_answer": user_answer_str,
            "correct_answer": q['answer'],
            "is_correct": correct == 1
        })
    
    score = (correct_count / total * 100) if total > 0 else 0
    c.execute('UPDATE exam_sessions SET completed=1, score=? WHERE id=?', (score, exam_id))
    conn.commit()
    conn.close()
    
    session.pop('current_exam_id', None)
    
    return jsonify({
        "success": True,
        "correct_count": correct_count,
        "total": total,
        "score": score,
        "results": question_results
    })
