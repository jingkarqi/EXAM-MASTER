import random
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, fetch_question, is_favorite, get_active_question_bank_id, get_active_ai_provider
from .auth import login_required, get_user_id, is_logged_in

bp = Blueprint('user', __name__)


@bp.route('/me')
@login_required
def personal_center():
    feature_cards = [
        {
            'title': '题库管理',
            'description': '切换、预览或删除题库，掌控当前答题源。',
            'endpoint': 'question_bank.list_banks',
            'icon': 'layer-group'
        },
        {
            'title': 'AI功能管理',
            'description': '管理 OpenAI 兼容服务，启用错题解析与提示。',
            'endpoint': 'ai.manage',
            'icon': 'robot'
        },
        {
            'title': '错题本',
            'description': '复习所有错题，进入错题练习模式。',
            'endpoint': 'user.wrong_questions',
            'icon': 'times-circle'
        },
        {
            'title': '我的收藏',
            'description': '管理标签、查看收藏的题目。',
            'endpoint': 'user.show_favorites',
            'icon': 'star'
        },
        {
            'title': '答题历史',
            'description': '回顾最近答题记录和表现趋势。',
            'endpoint': 'user.show_history',
            'icon': 'history'
        },
        {
            'title': '账号管理',
            'description': '修改用户名或密码，保护账号安全。',
            'endpoint': 'user.account_settings',
            'icon': 'user-cog'
        },
        {
            'title': '退出登录',
            'description': '结束本次会话，切换至其他账号。',
            'endpoint': 'auth.logout',
            'icon': 'sign-out-alt'
        }
    ]
    return render_template('user-dashboard.html', feature_cards=feature_cards)


@bp.route('/account')
@login_required
def account_settings():
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT username, created_at FROM users WHERE id=?', (user_id,))
    user = c.fetchone()
    conn.close()

    if not user:
        flash("未找到用户信息，请重新登录", "error")
        return redirect(url_for('auth.logout'))

    return render_template(
        'account.html',
        username=user['username'],
        created_at=user['created_at']
    )


@bp.route('/account/username', methods=['POST'])
@login_required
def update_username_settings():
    user_id = get_user_id()
    new_username = (request.form.get('new_username') or '').strip()

    if len(new_username) < 3:
        flash("新用户名至少需要 3 个字符。", "error")
        return redirect(url_for('user.account_settings'))

    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT id FROM users WHERE username=? AND id!=?', (new_username, user_id))
    exists = c.fetchone()
    if exists:
        conn.close()
        flash("用户名已被占用，请尝试其他名称。", "error")
        return redirect(url_for('user.account_settings'))

    c.execute('UPDATE users SET username=? WHERE id=?', (new_username, user_id))
    conn.commit()
    conn.close()
    flash("用户名更新成功。", "success")
    return redirect(url_for('user.account_settings'))


@bp.route('/account/password', methods=['POST'])
@login_required
def update_password_settings():
    user_id = get_user_id()
    current_password = request.form.get('current_password') or ''
    new_password = request.form.get('new_password') or ''
    confirm_password = request.form.get('confirm_password') or ''

    if not current_password or not new_password:
        flash("请输入完整的密码信息。", "error")
        return redirect(url_for('user.account_settings'))

    if new_password != confirm_password:
        flash("两次输入的新密码不一致。", "error")
        return redirect(url_for('user.account_settings'))

    if len(new_password) < 6:
        flash("新密码至少需要 6 个字符。", "error")
        return redirect(url_for('user.account_settings'))

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT password_hash FROM users WHERE id=?', (user_id,))
    user = c.fetchone()

    if not user or not check_password_hash(user['password_hash'], current_password):
        conn.close()
        flash("当前密码错误。", "error")
        return redirect(url_for('user.account_settings'))

    new_hash = generate_password_hash(new_password)
    c.execute('UPDATE users SET password_hash=? WHERE id=?', (new_hash, user_id))
    conn.commit()
    conn.close()
    flash("密码更新成功。", "success")
    return redirect(url_for('user.account_settings'))

@bp.route('/reset_history', methods=['POST'])
@login_required
def reset_history():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM history WHERE user_id=? AND question_bank_id=?', (user_id, question_bank_id))
        c.execute('UPDATE users SET current_seq_qid = NULL WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        flash("已清空当前题库的答题历史。", "success")
    except Exception as e:
        flash(f"重置历史时出错: {str(e)}", "error")
        
    return redirect(url_for('quiz.random_question'))

@bp.route('/history')
@login_required
def show_history():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM history WHERE user_id=? AND question_bank_id=? ORDER BY timestamp DESC',
              (user_id, question_bank_id))
    rows = c.fetchall()
    conn.close()
    
    history_data = []
    for r in rows:
        q = fetch_question(r['question_id'], question_bank_id)
        stem = q['stem'] if q else '题目已删除'
        history_data.append({
            'id': r['id'],
            'question_id': r['question_id'],
            'stem': stem,
            'user_answer': r['user_answer'],
            'correct': r['correct'],
            'timestamp': r['timestamp']
        })
    
    return render_template('history.html', history=history_data)

@bp.route('/wrong')
@login_required
def wrong_questions():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT question_id FROM history WHERE user_id=? AND question_bank_id=? AND correct=0',
              (user_id, question_bank_id))
    rows = c.fetchall()
    conn.close()
    
    wrong_ids = set(r['question_id'] for r in rows)
    questions_list = []
    
    for qid in wrong_ids:
        q = fetch_question(qid, question_bank_id)
        if q:
            questions_list.append(q)
    
    return render_template('wrong.html', questions=questions_list)

@bp.route('/only_wrong')
@login_required
def only_wrong_mode():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    has_ai_provider = bool(get_active_ai_provider(user_id))
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT question_id FROM history WHERE user_id=? AND question_bank_id=? AND correct=0',
              (user_id, question_bank_id))
    rows = c.fetchall()
    conn.close()
    
    wrong_ids = [r['question_id'] for r in rows]
    
    if not wrong_ids:
        flash("你没有错题或还未答题", "info")
        return redirect(url_for('main.index'))
    
    qid = random.choice(wrong_ids)
    q = fetch_question(qid, question_bank_id)
    is_fav = is_favorite(user_id, qid, question_bank_id)
    ai_context = {
        'enabled': bool(q) and has_ai_provider,
        'hasActiveProvider': has_ai_provider,
        'questionId': q['id'] if q else None,
        'questionBankId': question_bank_id,
        'hasSubmission': False,
        'userAnswer': '',
        'questionStem': q['stem'] if q else ''
    }
    
    return render_template('question.html', 
                          question=q, 
                          is_favorite=is_fav,
                          user_answer='',
                          ai_context=ai_context)

@bp.route('/favorite/<qid>', methods=['POST'])
@login_required
def favorite_question(qid):
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('INSERT OR IGNORE INTO favorites (user_id, question_id, question_bank_id, tag) VALUES (?,?,?,?)',
                  (user_id, qid, question_bank_id, ''))
        conn.commit()
        flash("收藏成功！", "success")
    except Exception as e:
        flash(f"收藏失败: {str(e)}", "error")
    finally:
        conn.close()
    
    referrer = request.referrer
    if referrer and '/question/' in referrer:
        return redirect(referrer)
    return redirect(url_for('quiz.show_question', qid=qid))

@bp.route('/unfavorite/<qid>', methods=['POST'])
@login_required
def unfavorite_question(qid):
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('DELETE FROM favorites WHERE user_id=? AND question_id=? AND question_bank_id=?',
                  (user_id, qid, question_bank_id))
        conn.commit()
        flash("已取消收藏", "success")
    except Exception as e:
        flash(f"取消收藏失败: {str(e)}", "error")
    finally:
        conn.close()
    
    referrer = request.referrer
    if referrer and '/question/' in referrer:
        return redirect(referrer)
    return redirect(url_for('quiz.show_question', qid=qid))

@bp.route('/update_tag/<qid>', methods=['POST'])
@login_required
def update_tag(qid):
    # 注意：这里直接用了 is_logged_in，因为该路由通常是 AJAX 调用
    if not is_logged_in():
        return jsonify({"success": False, "msg": "未登录"}), 401
    
    user_id = get_user_id()
    new_tag = request.form.get('tag', '')
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('UPDATE favorites SET tag=? WHERE user_id=? AND question_id=? AND question_bank_id=?',
                  (new_tag, user_id, qid, get_active_question_bank_id(user_id)))
        conn.commit()
        return jsonify({"success": True, "msg": "标记更新成功"})
    except Exception as e:
        return jsonify({"success": False, "msg": f"更新失败: {str(e)}"}), 500
    finally:
        conn.close()

@bp.route('/favorites')
@login_required
def show_favorites():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT f.question_id, f.tag, q.stem 
        FROM favorites f 
        JOIN questions q ON f.question_id=q.id AND f.question_bank_id = q.question_bank_id
        WHERE f.user_id=? AND f.question_bank_id=?
    ''', (user_id, question_bank_id))
    rows = c.fetchall()
    conn.close()
    
    favorites_data = [{'question_id': r['question_id'], 'tag': r['tag'], 'stem': r['stem']} for r in rows]
    return render_template('favorites.html', favorites=favorites_data)

@bp.route('/statistics')
@login_required
def statistics():
    user_id = get_user_id()
    question_bank_id = get_active_question_bank_id(user_id)
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT COUNT(*) as total, SUM(correct) as correct_count FROM history WHERE user_id=? AND question_bank_id=?',
              (user_id, question_bank_id))
    row = c.fetchone()
    total = row['total'] if row['total'] else 0
    correct_count = row['correct_count'] if row['correct_count'] else 0
    overall_accuracy = (correct_count/total*100) if total>0 else 0
    
    c.execute('''
        SELECT q.difficulty, COUNT(*) as total, SUM(h.correct) as correct_count
        FROM history h 
        JOIN questions q ON h.question_id=q.id AND h.question_bank_id = q.question_bank_id
        WHERE h.user_id=? AND h.question_bank_id=?
        GROUP BY q.difficulty
    ''', (user_id, question_bank_id))
    difficulty_stats = []
    for r in c.fetchall():
        difficulty_stats.append({
            'difficulty': r['difficulty'] or '未分类',
            'total': r['total'],
            'correct_count': r['correct_count'],
            'accuracy': (r['correct_count']/r['total']*100) if r['total']>0 else 0
        })
    
    c.execute('''
        SELECT q.category, COUNT(*) as total, SUM(h.correct) as correct_count
        FROM history h 
        JOIN questions q ON h.question_id=q.id AND h.question_bank_id = q.question_bank_id
        WHERE h.user_id=? AND h.question_bank_id=?
        GROUP BY q.category
    ''', (user_id, question_bank_id))
    category_stats = []
    for r in c.fetchall():
        category_stats.append({
            'category': r['category'] or '未分类',
            'total': r['total'],
            'correct_count': r['correct_count'],
            'accuracy': (r['correct_count']/r['total']*100) if r['total']>0 else 0
        })
    
    c.execute('''
        SELECT h.question_id, COUNT(*) as wrong_times, q.stem
        FROM history h 
        JOIN questions q ON h.question_id=q.id AND h.question_bank_id = q.question_bank_id
        WHERE h.user_id=? AND h.question_bank_id=? AND h.correct=0
        GROUP BY h.question_id ORDER BY wrong_times DESC LIMIT 10
    ''', (user_id, question_bank_id))
    worst_questions = []
    for r in c.fetchall():
        worst_questions.append({
            'question_id': r['question_id'],
            'stem': r['stem'],
            'wrong_times': r['wrong_times']
        })
    
    c.execute('''
        SELECT id, mode, start_time, score, (SELECT COUNT(*) FROM JSON_EACH(question_ids)) as question_count
        FROM exam_sessions WHERE user_id=? AND question_bank_id=? AND completed=1
        ORDER BY start_time DESC LIMIT 5
    ''', (user_id, question_bank_id))
    recent_exams = []
    for r in c.fetchall():
        recent_exams.append({
            'id': r['id'],
            'mode': r['mode'],
            'start_time': r['start_time'],
            'score': r['score'],
            'question_count': r['question_count']
        })
    
    conn.close()
    return render_template('statistics.html', 
                          overall_accuracy=overall_accuracy,
                          difficulty_stats=difficulty_stats,
                          category_stats=category_stats,
                          worst_questions=worst_questions,
                          recent_exams=recent_exams)
