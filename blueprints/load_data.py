import os
import json
import csv
import tempfile
import uuid
from datetime import datetime
from flask import Blueprint, request, render_template, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from database import (
    get_db,
    get_user_question_banks,
    get_active_question_bank_id,
    create_question_bank,
    set_active_question_bank_id,
    user_can_access_bank,
    get_question_bank_summary,
    SYSTEM_QUESTION_BANK_ID,
    SYSTEM_QUESTION_BANK_NAME,
)
from .auth import login_required, get_user_id

bp = Blueprint('load_data', __name__)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'csv', 'txt'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
IMPORT_STASH_DIR = os.path.join(tempfile.gettempdir(), 'exam_master_imports')

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_question_data(question_data):
    """验证题目数据的有效性"""
    errors = []

    # 检查必填字段
    required_fields = ['id', 'stem', 'answer']
    for field in required_fields:
        if not question_data.get(field) or not str(question_data[field]).strip():
            errors.append(f"字段 '{field}' 不能为空")

    # 标准化题型
    question_type = (question_data.get('qtype') or '单选题').strip() or '单选题'
    question_data['qtype'] = question_type

    if question_type not in ['单选题', '多选题', '判断题', '填空题']:
        errors.append(f"题型 '{question_type}' 无效，必须是：单选题、多选题、判断题、填空题")
        return errors

    normalized_answer = str(question_data.get('answer', '')).strip()

    if question_type in ['单选题', '多选题']:
        answer = normalized_answer.upper()
        question_data['answer'] = answer
        for char in answer:
            if char not in 'ABCDE':
                errors.append(f"答案 '{answer}' 包含无效字符，只能包含 A-E")
                break

        options_count = 0
        for opt in ['A', 'B', 'C', 'D', 'E']:
            if question_data.get(opt) and str(question_data[opt]).strip():
                options_count += 1

        if options_count < 2:
            errors.append("至少需要提供2个选项")

    elif question_type == '判断题':
        if normalized_answer not in ['正确', '错误']:
            errors.append("判断题答案必须为“正确”或“错误”")
        question_data['answer'] = normalized_answer
    else:  # 填空题
        question_data['answer'] = normalized_answer

    return errors

def parse_csv_file(file_path):
    """解析CSV文件并返回题目数据"""
    questions = []
    errors = []

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):  # 从第2行开始（跳过表头）
                question_type = (row.get('题型', '单选题') or '单选题').strip() or '单选题'
                raw_answer = row.get('答案', '').strip()
                answer_value = raw_answer.upper() if question_type in ['单选题', '多选题'] else raw_answer

                question_data = {
                    'id': row.get('题号', '').strip(),
                    'stem': row.get('题干', '').strip(),
                    'answer': answer_value,
                    'difficulty': row.get('难度', '无').strip(),
                    'qtype': question_type,
                    'category': row.get('类别', '未分类').strip(),
                    'A': row.get('A', '').strip(),
                    'B': row.get('B', '').strip(),
                    'C': row.get('C', '').strip(),
                    'D': row.get('D', '').strip(),
                    'E': row.get('E', '').strip()
                }

                # 验证题目数据
                validation_errors = validate_question_data(question_data)
                if validation_errors:
                    errors.append({
                        'row': row_num,
                        'id': question_data['id'],
                        'errors': validation_errors
                    })
                else:
                    questions.append(question_data)

    except Exception as e:
        errors.append({
            'row': 0,
            'id': 'unknown',
            'errors': [f"文件解析错误: {str(e)}"]
        })

    return questions, errors

def parse_txt_file(file_path):
    """解析TXT文件并返回题目数据"""
    # 这里可以复用现有的转换工具逻辑
    # 暂时返回空列表，后续可以集成现有转换工具
    return [], [{'row': 0, 'id': 'unknown', 'errors': ['TXT格式支持正在开发中']}]

def ensure_stash_dir():
    """确保用于暂存导入数据的目录存在"""
    os.makedirs(IMPORT_STASH_DIR, exist_ok=True)
    return IMPORT_STASH_DIR

def stash_import_payload(questions, errors, filename, target_bank):
    """将解析结果保存在临时JSON文件中，并返回唯一ID"""
    ensure_stash_dir()
    job_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}"
    stash_path = os.path.join(IMPORT_STASH_DIR, f"{job_id}.json")
    payload = {
        'questions': questions,
        'errors': errors,
        'filename': filename,
        'target_bank': target_bank
    }
    with open(stash_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False)
    return job_id

def load_stashed_payload(job_id):
    """根据唯一ID读取已暂存的导入数据"""
    if not job_id:
        return None
    stash_path = os.path.join(ensure_stash_dir(), f"{job_id}.json")
    if not os.path.exists(stash_path):
        return None
    with open(stash_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def delete_stashed_payload(job_id):
    """删除指定ID的暂存文件"""
    if not job_id:
        return
    stash_path = os.path.join(ensure_stash_dir(), f"{job_id}.json")
    if os.path.exists(stash_path):
        os.unlink(stash_path)

@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """文件上传页面"""
    user_id = get_user_id()
    banks = get_user_question_banks(user_id)
    active_bank_id = get_active_question_bank_id(user_id)
    target_bank_info = None

    if request.method == 'POST':
        target_mode = request.form.get('target_mode', 'existing')
        if target_mode == 'existing':
            existing_bank_id_raw = request.form.get('existing_bank_id', str(active_bank_id or SYSTEM_QUESTION_BANK_ID))
            try:
                existing_bank_id = int(existing_bank_id_raw)
            except (TypeError, ValueError):
                existing_bank_id = SYSTEM_QUESTION_BANK_ID

            if not user_can_access_bank(user_id, existing_bank_id):
                flash('无权访问所选题库', 'error')
                return redirect(request.url)

            target_bank_info = {
                'mode': 'existing',
                'bank_id': existing_bank_id
            }
        else:
            new_bank_name = request.form.get('new_bank_name', '').strip()
            new_bank_desc = request.form.get('new_bank_description', '').strip()
            if not new_bank_name:
                flash('请填写新题库名称', 'error')
                return redirect(request.url)
            target_bank_info = {
                'mode': 'new',
                'name': new_bank_name,
                'description': new_bank_desc
            }

        # 检查是否有文件
        if 'file' not in request.files:
            flash('请选择要上传的文件', 'error')
            return redirect(request.url)

        file = request.files['file']

        # 检查文件名
        if file.filename == '':
            flash('请选择要上传的文件', 'error')
            return redirect(request.url)

        # 检查文件类型
        if not allowed_file(file.filename):
            flash('只支持 CSV 和 TXT 格式的文件', 'error')
            return redirect(request.url)

        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 回到文件开头

        if file_size > MAX_FILE_SIZE:
            flash(f'文件大小不能超过 {MAX_FILE_SIZE // 1024 // 1024}MB', 'error')
            return redirect(request.url)

        # 保存临时文件
        filename = secure_filename(file.filename)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}")

        try:
            file.save(temp_path)

            # 根据文件类型解析
            file_ext = filename.rsplit('.', 1)[1].lower()
            if file_ext == 'csv':
                questions, errors = parse_csv_file(temp_path)
            elif file_ext == 'txt':
                questions, errors = parse_txt_file(temp_path)
            else:
                questions, errors = [], []

            # 清理之前的暂存文件，避免堆积
            previous_job_id = session.pop('import_job_id', None)
            delete_stashed_payload(previous_job_id)

            # 保存解析结果到临时文件，仅在session中保存引用ID
            job_id = stash_import_payload(questions, errors, filename, target_bank_info)
            session['import_job_id'] = job_id

            # 清理临时文件
            os.unlink(temp_path)

            # 如果有错误，显示错误页面
            if errors:
                return redirect(url_for('load_data.preview'))

            # 如果没有错误，直接跳转到导入确认
            return redirect(url_for('load_data.preview'))

        except Exception as e:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            flash(f'文件处理失败: {str(e)}', 'error')
            return redirect(request.url)

    return render_template('import.html',
                           banks=banks,
                           active_bank_id=active_bank_id,
                           system_bank_name=SYSTEM_QUESTION_BANK_NAME)

@bp.route('/preview', methods=['GET', 'POST'])
@login_required
def preview():
    """预览和确认导入页面"""
    job_id = session.get('import_job_id')
    payload = load_stashed_payload(job_id)
    user_id = get_user_id()

    if payload:
        questions = payload.get('questions', [])
        errors = payload.get('errors', [])
        filename = payload.get('filename', '')
        target_bank_raw = payload.get('target_bank')
    else:
        questions = []
        errors = []
        filename = ''
        target_bank_raw = None

    def resolve_target_bank(raw_bank):
        context = {
            'mode': 'existing',
            'display_name': SYSTEM_QUESTION_BANK_NAME,
            'description': '平台预置题库',
            'bank_id': SYSTEM_QUESTION_BANK_ID,
            'is_system': True
        }

        if isinstance(raw_bank, dict):
            mode = raw_bank.get('mode', 'existing')
            if mode == 'new':
                context.update({
                    'mode': 'new',
                    'display_name': raw_bank.get('name', '新题库'),
                    'description': raw_bank.get('description', ''),
                    'bank_id': None,
                    'is_system': False
                })
            else:
                try:
                    bank_id = int(raw_bank.get('bank_id', SYSTEM_QUESTION_BANK_ID))
                except (TypeError, ValueError):
                    bank_id = SYSTEM_QUESTION_BANK_ID
                summary = get_question_bank_summary(bank_id, user_id)
                if summary:
                    context.update({
                        'display_name': summary['name'],
                        'description': summary['description'],
                        'bank_id': bank_id,
                        'is_system': summary['is_system'],
                        'question_count': summary['question_count'],
                        'last_updated': summary['last_updated']
                    })
                else:
                    context.update({
                        'bank_id': bank_id,
                        'display_name': '未知题库',
                        'description': '',
                        'is_system': False
                    })
        return context

    target_bank_context = resolve_target_bank(target_bank_raw)

    # 检查 session 数据
    if not questions and not errors:
        flash('请先上传文件', 'error')
        return redirect(url_for('load_data.upload'))

    if request.method == 'POST':
        # 执行导入
        target_bank_payload = target_bank_raw or {'mode': 'existing', 'bank_id': SYSTEM_QUESTION_BANK_ID}
        target_mode = target_bank_payload.get('mode', 'existing')
        bank_name_for_flash = SYSTEM_QUESTION_BANK_NAME

        if target_mode == 'new':
            bank_name_for_flash = target_bank_payload.get('name', '新题库')
            bank_description = target_bank_payload.get('description', '')
            bank_id = create_question_bank(user_id, bank_name_for_flash, bank_description)
            set_active_question_bank_id(user_id, bank_id)
        else:
            try:
                bank_id = int(target_bank_payload.get('bank_id', SYSTEM_QUESTION_BANK_ID))
            except (TypeError, ValueError):
                bank_id = SYSTEM_QUESTION_BANK_ID

            if not user_can_access_bank(user_id, bank_id):
                flash('无权导入到所选题库', 'error')
                return redirect(url_for('load_data.upload'))

            summary = get_question_bank_summary(bank_id, user_id)
            if summary:
                bank_name_for_flash = summary['name']

        conn = get_db()
        c = conn.cursor()

        success_count = 0
        error_count = 0

        try:
            for question in questions:
                # 构建选项JSON
                options = {}
                for opt in ['A', 'B', 'C', 'D', 'E']:
                    if question.get(opt) and str(question[opt]).strip():
                        options[opt] = question[opt]

                # 插入题目到数据库
                c.execute(
                    """INSERT INTO questions
                       (id, stem, answer, difficulty, qtype, category, options, question_type, question_bank_id)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        question['id'],
                        question['stem'],
                        question['answer'],
                        question['difficulty'],
                        question['qtype'],
                        question['category'],
                        json.dumps(options, ensure_ascii=False),
                        question['qtype'],  # 使用qtype作为question_type
                        bank_id
                    )
                )
                success_count += 1

            conn.commit()

            # 清理session数据
            session.pop('import_job_id', None)
            delete_stashed_payload(job_id)

            flash(f'成功导入 {success_count} 道题目到「{bank_name_for_flash}」', 'success')
            return redirect(url_for('main.index'))

        except Exception as e:
            conn.rollback()
            flash(f'导入失败: {str(e)}', 'error')

        finally:
            conn.close()

    return render_template('import_preview.html',
                          questions=questions,
                          errors=errors,
                          filename=filename,
                          target_bank=target_bank_context)

@bp.route('/cancel', methods=['POST'])
@login_required
def cancel():
    """取消导入"""
    # 清理session数据
    job_id = session.pop('import_job_id', None)
    delete_stashed_payload(job_id)

    flash('导入已取消', 'info')
    return redirect(url_for('main.index'))
