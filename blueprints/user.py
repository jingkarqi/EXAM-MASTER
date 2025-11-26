import random
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from database import get_db, fetch_question, is_favorite, get_active_question_bank_id
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
        }
    ]
    return render_template('user-dashboard.html', feature_cards=feature_cards)

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
    
    return render_template('question.html', 
                          question=q, 
                          is_favorite=is_fav)

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
