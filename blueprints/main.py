import os
from datetime import datetime
from flask import Blueprint, render_template, send_file, abort, current_app
from database import get_db, get_active_question_bank_id, get_question_bank_summary
from .auth import login_required, get_user_id

bp = Blueprint('main', __name__)

@bp.route('/')
@login_required
def index():
    """Home page route."""
    user_id = get_user_id()
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT current_seq_qid FROM users WHERE id = ?', (user_id,))
    user_data = c.fetchone()
    current_seq_qid = user_data['current_seq_qid'] if user_data and user_data['current_seq_qid'] else None
    conn.close()

    active_bank_id = get_active_question_bank_id(user_id)
    active_bank_summary = get_question_bank_summary(active_bank_id, user_id)
    
    return render_template('index.html', 
                          current_year=datetime.now().year,
                          current_seq_qid=current_seq_qid,
                          active_bank_summary=active_bank_summary)

@bp.route('/ExamMasterAndroid/<filename>')
def download_apk(filename):
    """Handle APK file downloads."""
    try:
        if not filename.endswith('.apk'):
            abort(404)
        
        # 使用 current_app.root_path 确保路径正确
        script_dir = current_app.root_path
        apk_path = os.path.join(script_dir, 'ExamMasterAndroid', filename)
        
        if not os.path.exists(apk_path):
            abort(404)
        
        return send_file(
            apk_path, 
            as_attachment=True, 
            download_name=filename,
            mimetype='application/vnd.android.package-archive'
        )
        
    except Exception as e:
        print(f"Error in download_apk: {e}")
        abort(404)

# Error handlers usually attach to app, but via blueprint we use app_errorhandler
@bp.app_errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_code=404, error_message="页面不存在"), 404

@bp.app_errorhandler(500)
def server_error(e):
    return render_template('error.html', error_code=500, error_message="服务器内部错误"), 500
