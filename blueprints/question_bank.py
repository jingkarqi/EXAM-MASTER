from flask import Blueprint, render_template, redirect, url_for, flash

from database import (
    get_user_question_banks,
    get_active_question_bank_id,
    set_active_question_bank_id,
    get_question_bank_summary,
    get_question_bank_preview,
    delete_question_bank,
    user_can_access_bank,
    SYSTEM_QUESTION_BANK_ID,
)
from .auth import login_required, get_user_id

bp = Blueprint('question_bank', __name__, url_prefix='/question-banks')


@bp.route('/', methods=['GET'])
@login_required
def list_banks():
    """题库管理首页"""
    user_id = get_user_id()
    banks = get_user_question_banks(user_id)
    active_bank_id = get_active_question_bank_id(user_id)
    enriched = []
    for bank in banks:
        summary = get_question_bank_summary(bank['id'], user_id)
        enriched.append({
            **bank,
            'summary': summary
        })
    active_summary = get_question_bank_summary(active_bank_id, user_id)
    return render_template('question_banks.html',
                           banks=enriched,
                           active_bank_id=active_bank_id,
                           active_summary=active_summary)


@bp.route('/activate/<int:bank_id>', methods=['POST'])
@login_required
def activate_bank(bank_id):
    """切换当前题库"""
    user_id = get_user_id()
    if not user_can_access_bank(user_id, bank_id):
        flash('无权访问该题库', 'error')
    else:
        try:
            set_active_question_bank_id(user_id, bank_id)
            summary = get_question_bank_summary(bank_id, user_id)
            name = summary['name'] if summary else '题库'
            flash(f'已切换至「{name}」', 'success')
        except ValueError as exc:
            flash(str(exc), 'error')
    return redirect(url_for('question_bank.list_banks'))


@bp.route('/delete/<int:bank_id>', methods=['POST'])
@login_required
def delete_bank(bank_id):
    """删除自定义题库"""
    user_id = get_user_id()
    if bank_id == SYSTEM_QUESTION_BANK_ID:
        flash('系统默认题库不可删除', 'error')
        return redirect(url_for('question_bank.list_banks'))

    summary = get_question_bank_summary(bank_id, user_id)
    name = summary['name'] if summary else '题库'
    if delete_question_bank(user_id, bank_id):
        flash(f'已删除「{name}」', 'success')
    else:
        flash('题库不存在或无权删除', 'error')
    return redirect(url_for('question_bank.list_banks'))


@bp.route('/preview/<int:bank_id>', methods=['GET'])
@login_required
def preview_bank(bank_id):
    """预览题库内容"""
    user_id = get_user_id()
    if not user_can_access_bank(user_id, bank_id):
        flash('无权访问该题库', 'error')
        return redirect(url_for('question_bank.list_banks'))

    summary = get_question_bank_summary(bank_id, user_id)
    if not summary:
        flash('题库不存在', 'error')
        return redirect(url_for('question_bank.list_banks'))

    questions = get_question_bank_preview(bank_id, limit=20)
    is_active = bank_id == get_active_question_bank_id(user_id)
    return render_template('question_bank_preview.html',
                           summary=summary,
                           questions=questions,
                           is_active=is_active)
