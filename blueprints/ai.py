from flask import Blueprint, Response, flash, jsonify, redirect, render_template, request, stream_with_context, url_for

from ai_service import (
    AIServiceError,
    build_analysis_messages,
    build_hint_messages,
    decrypt_api_key,
    encrypt_api_key,
    stream_chat_completion,
    validate_provider_connection,
)
from blueprints.auth import get_user_id, login_required
from database import (
    SYSTEM_QUESTION_BANK_ID,
    fetch_question,
    get_active_ai_provider,
    get_ai_provider,
    get_ai_providers,
    get_db,
)

bp = Blueprint('ai', __name__, url_prefix='/ai')


def _normalize_url(url: str) -> str:
    return (url or '').strip().rstrip('/')


def _validate_and_update(conn, provider_row, decrypted_key):
    payload = {
        'base_url': provider_row['base_url'],
        'model': provider_row['model'],
        'api_key': decrypted_key
    }
    is_valid, message = validate_provider_connection(payload)
    c = conn.cursor()
    c.execute('''
        UPDATE ai_providers
        SET is_valid=?,
            last_verified_at=CURRENT_TIMESTAMP,
            last_error=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=? AND user_id=?
    ''', (1 if is_valid else 0, None if is_valid else message[:500], provider_row['id'], provider_row['user_id']))
    conn.commit()
    return is_valid, message


@bp.route('/manage')
@login_required
def manage():
    user_id = get_user_id()
    providers = get_ai_providers(user_id)
    active = get_active_ai_provider(user_id)
    return render_template('ai-manage.html', providers=providers, has_active=bool(active))


@bp.route('/providers', methods=['POST'])
@login_required
def create_provider():
    user_id = get_user_id()
    provider_name = (request.form.get('provider_name') or '').strip()
    base_url = _normalize_url(request.form.get('base_url') or '')
    model = (request.form.get('model') or '').strip()
    api_key = (request.form.get('api_key') or '').strip()

    if not provider_name or not base_url or not model or not api_key:
        flash('请完整填写服务名称、基础 URL、模型 ID 与 API 密钥。', 'error')
        return redirect(url_for('ai.manage'))
    if not base_url.startswith('http'):
        flash('基础 URL 必须包含 http/https 协议。', 'error')
        return redirect(url_for('ai.manage'))

    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) as total FROM ai_providers WHERE user_id=?', (user_id,))
    has_existing = c.fetchone()['total'] > 0

    try:
        encrypted_key = encrypt_api_key(api_key)
    except Exception as exc:
        conn.close()
        flash(f'保存密钥失败: {exc}', 'error')
        return redirect(url_for('ai.manage'))

    c.execute('''
        INSERT INTO ai_providers (user_id, provider_name, base_url, model, api_key_encrypted, is_active)
        VALUES (?,?,?,?,?,?)
    ''', (user_id, provider_name, base_url, model, encrypted_key, 0 if has_existing else 1))
    provider_id = c.lastrowid
    conn.commit()

    provider_row = {
        'id': provider_id,
        'user_id': user_id,
        'base_url': base_url,
        'model': model
    }
    is_valid, message = _validate_and_update(conn, provider_row, api_key)
    conn.close()

    flash('AI 服务配置已保存。', 'success')
    if not has_existing:
        flash('已自动激活首个配置。', 'success')

    if is_valid:
        flash('配置验证成功，服务可用。', 'success')
    else:
        flash(f'配置验证失败: {message}', 'error')

    return redirect(url_for('ai.manage'))


@bp.route('/providers/<int:provider_id>/update', methods=['POST'])
@login_required
def update_provider(provider_id):
    user_id = get_user_id()
    provider = get_ai_provider(provider_id, user_id)
    if not provider:
        flash('未找到该配置。', 'error')
        return redirect(url_for('ai.manage'))

    provider_name = (request.form.get('provider_name') or provider['provider_name']).strip()
    base_url = _normalize_url(request.form.get('base_url') or provider['base_url'])
    model = (request.form.get('model') or provider['model']).strip()
    new_api_key = (request.form.get('api_key') or '').strip()

    if not provider_name or not base_url or not model:
        flash('服务名称、基础 URL、模型 ID 不能为空。', 'error')
        return redirect(url_for('ai.manage'))
    if not base_url.startswith('http'):
        flash('基础 URL 必须包含 http/https 协议。', 'error')
        return redirect(url_for('ai.manage'))

    conn = get_db()
    c = conn.cursor()

    encrypted_key = provider['api_key_encrypted']
    decrypted_key = None
    if new_api_key:
        try:
            encrypted_key = encrypt_api_key(new_api_key)
            decrypted_key = new_api_key
        except Exception as exc:
            conn.close()
            flash(f'更新密钥失败: {exc}', 'error')
            return redirect(url_for('ai.manage'))
    else:
        try:
            decrypted_key = decrypt_api_key(provider['api_key_encrypted'])
        except AIServiceError as exc:
            conn.close()
            flash(str(exc), 'error')
            return redirect(url_for('ai.manage'))

    c.execute('''
        UPDATE ai_providers
        SET provider_name=?, base_url=?, model=?, api_key_encrypted=?, updated_at=CURRENT_TIMESTAMP
        WHERE id=? AND user_id=?
    ''', (provider_name, base_url, model, encrypted_key, provider_id, user_id))
    conn.commit()

    provider_row = {
        'id': provider_id,
        'user_id': user_id,
        'base_url': base_url,
        'model': model
    }
    is_valid, message = _validate_and_update(conn, provider_row, decrypted_key)
    conn.close()

    flash('AI 服务配置已更新。', 'success')
    if is_valid:
        flash('验证成功。', 'success')
    else:
        flash(f'验证失败: {message}', 'error')
    return redirect(url_for('ai.manage'))


@bp.route('/providers/<int:provider_id>/activate', methods=['POST'])
@login_required
def activate_provider(provider_id):
    user_id = get_user_id()
    provider = get_ai_provider(provider_id, user_id)
    if not provider:
        flash('未找到该配置。', 'error')
        return redirect(url_for('ai.manage'))

    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE ai_providers SET is_active=0 WHERE user_id=?', (user_id,))
    c.execute('UPDATE ai_providers SET is_active=1, updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?',
              (provider_id, user_id))
    conn.commit()
    conn.close()

    flash(f'已激活 {provider["provider_name"]}。', 'success')
    return redirect(url_for('ai.manage'))


@bp.route('/providers/<int:provider_id>/delete', methods=['POST'])
@login_required
def delete_provider(provider_id):
    user_id = get_user_id()
    provider = get_ai_provider(provider_id, user_id)
    if not provider:
        flash('未找到该配置。', 'error')
        return redirect(url_for('ai.manage'))

    conn = get_db()
    c = conn.cursor()
    c.execute('DELETE FROM ai_providers WHERE id=? AND user_id=?', (provider_id, user_id))
    conn.commit()

    if provider['is_active']:
        c.execute('''
            UPDATE ai_providers
            SET is_active=1, updated_at=CURRENT_TIMESTAMP
            WHERE id=(
                SELECT id FROM ai_providers WHERE user_id=? ORDER BY updated_at DESC LIMIT 1
            )
        ''', (user_id,))
        conn.commit()
    conn.close()

    flash('配置已删除。', 'success')
    return redirect(url_for('ai.manage'))


@bp.route('/providers/<int:provider_id>/validate', methods=['POST'])
@login_required
def validate_provider(provider_id):
    user_id = get_user_id()
    provider = get_ai_provider(provider_id, user_id)
    if not provider:
        flash('未找到该配置。', 'error')
        return redirect(url_for('ai.manage'))

    try:
        decrypted_key = decrypt_api_key(provider['api_key_encrypted'])
    except AIServiceError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('ai.manage'))

    conn = get_db()
    provider_row = {
        'id': provider_id,
        'user_id': user_id,
        'base_url': provider['base_url'],
        'model': provider['model']
    }
    is_valid, message = _validate_and_update(conn, provider_row, decrypted_key)
    conn.close()

    if is_valid:
        flash('验证成功。', 'success')
    else:
        flash(f'验证失败: {message}', 'error')
    return redirect(url_for('ai.manage'))


@bp.route('/run', methods=['POST'])
@login_required
def run_ai():
    user_id = get_user_id()
    provider = get_active_ai_provider(user_id)
    if not provider:
        return jsonify({'error': '请先在“我的 > AI功能管理”中配置并激活 AI 服务。'}), 400

    payload = request.get_json(silent=True) or {}
    mode = payload.get('mode')
    question_id = payload.get('question_id')
    question_bank_id = payload.get('question_bank_id', SYSTEM_QUESTION_BANK_ID)
    user_answer = payload.get('user_answer', '')

    if not question_id:
        return jsonify({'error': '缺少题目编号，无法生成解析。'}), 400

    question = fetch_question(str(question_id), question_bank_id)
    if not question:
        return jsonify({'error': '题目不存在或已被删除。'}), 404

    try:
        api_key = decrypt_api_key(provider['api_key_encrypted'])
    except AIServiceError as exc:
        return jsonify({'error': str(exc)}), 400

    provider_payload = {
        'base_url': provider['base_url'],
        'model': provider['model'],
        'api_key': api_key
    }

    try:
        if mode == 'analysis':
            messages = build_analysis_messages(question, user_answer)
            temperature = 0.2
        elif mode == 'hint':
            messages = build_hint_messages(question)
            temperature = 0.5
        else:
            return jsonify({'error': '未知的 AI 模式。'}), 400
    except AIServiceError as exc:
        return jsonify({'error': str(exc)}), 400

    def generate():
        try:
            for chunk in stream_chat_completion(provider_payload, messages, temperature=temperature):
                yield chunk
        except AIServiceError as exc:
            yield f"\n\n[ERROR] {exc}"

    return Response(stream_with_context(generate()), mimetype='text/plain; charset=utf-8')
