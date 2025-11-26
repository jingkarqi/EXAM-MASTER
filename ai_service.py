import base64
import hashlib
import json
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import requests
from cryptography.fernet import Fernet, InvalidToken
from flask import current_app


class AIServiceError(Exception):
    """Raised when downstream AI services fail or are misconfigured."""


_BASE_DIR = Path(__file__).resolve().parent
_PROMPT_DIR = _BASE_DIR / 'prompt'
_DEBUG_DIR = _BASE_DIR / 'debug'
_DEBUG_LOG_PATH = _DEBUG_DIR / 'ai_stream.log'


def _get_cipher() -> Fernet:
    secret = current_app.config.get('SECRET_KEY')
    if not secret:
        raise AIServiceError('SECRET_KEY 未配置，无法完成 API 密钥的加解密。')
    digest = hashlib.sha256(secret.encode('utf-8')).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_api_key(raw: str) -> str:
    if not raw:
        raise ValueError('API 密钥不能为空')
    cipher = _get_cipher()
    return cipher.encrypt(raw.encode('utf-8')).decode('utf-8')


def decrypt_api_key(token: str) -> str:
    if not token:
        raise AIServiceError('未配置 API 密钥')
    cipher = _get_cipher()
    try:
        return cipher.decrypt(token.encode('utf-8')).decode('utf-8')
    except InvalidToken as exc:
        raise AIServiceError('无法解密 API 密钥，请重新保存配置。') from exc


@lru_cache(maxsize=8)
def load_prompt(name: str) -> str:
    path = _PROMPT_DIR / f'{name}.md'
    if not path.exists():
        raise AIServiceError(f'未找到 {name}.md 提示词，请检查 prompt 目录。')
    return path.read_text(encoding='utf-8')


def _append_debug_log(event: str, payload: Dict) -> None:
    """
    将 AI 流式交互过程中的关键数据记录到 debug/ai_stream.log 方便排障。
    """
    try:
        _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'event': event,
            **payload
        }
        with _DEBUG_LOG_PATH.open('a', encoding='utf-8') as log_file:
            log_file.write(json.dumps(record, ensure_ascii=False) + '\n')
    except Exception:
        # 调试日志失败不能影响主流程
        pass


def _format_options(options: Dict[str, str]) -> str:
    if not options:
        return '无选项（判断/填空题）。'
    return '\n'.join([f'{k}. {v}' for k, v in options.items()])


def format_question_block(question: Dict) -> str:
    lines = [
        f"题号: {question.get('id')}",
        f"题型: {question.get('question_type') or question.get('type')}",
        f"难度: {question.get('difficulty') or '未设定'}",
        f"分类: {question.get('category') or '未分类'}",
        f"题干: {question.get('stem')}",
        '选项:',
        _format_options(question.get('options') or {}),
        f"标准答案: {question.get('answer')}"
    ]
    return '\n'.join(lines)


def build_analysis_messages(question: Dict, user_answer: str) -> List[Dict[str, str]]:
    system_msg = {'role': 'system', 'content': load_prompt('analysis')}
    user_lines = [
        format_question_block(question),
        f"用户作答: {user_answer or '未作答'}",
        '请根据提示词输出完整解析。'
    ]
    return [system_msg, {'role': 'user', 'content': '\n'.join(user_lines)}]


def build_hint_messages(question: Dict) -> List[Dict[str, str]]:
    system_msg = {'role': 'system', 'content': load_prompt('hint')}
    user_lines = [
        format_question_block(question),
        '请在不透露答案的前提下，输出循序渐进的思路提示。'
    ]
    return [system_msg, {'role': 'user', 'content': '\n'.join(user_lines)}]


def _build_headers(api_key: str) -> Dict[str, str]:
    return {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }


def _build_payload(model: str, messages: List[Dict[str, str]], *, stream: bool = True, temperature: float = 0.2) -> Dict:
    return {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'stream': stream
    }


def stream_chat_completion(provider: Dict, messages: List[Dict[str, str]], *, temperature: float = 0.2,
                           timeout: int = 15, retry_delay: int = 5) -> Iterable[str]:
    url = provider['base_url'].rstrip('/') + '/v1/chat/completions'
    headers = _build_headers(provider['api_key'])
    payload = _build_payload(provider['model'], messages, stream=True, temperature=temperature)
    last_error = None
    trace_id = str(uuid.uuid4())
    _append_debug_log('request.start', {
        'trace_id': trace_id,
        'base_url': provider['base_url'],
        'model': provider['model'],
        'temperature': temperature,
        'messages': messages
    })
    for attempt in range(2):
        aggregated_output: List[str] = []
        try:
            with requests.post(url, headers=headers, json=payload, timeout=timeout, stream=True) as resp:
                if resp.status_code >= 400:
                    _append_debug_log('response.http_error', {
                        'trace_id': trace_id,
                        'status': resp.status_code,
                        'body': resp.text[:500]
                    })
                    raise AIServiceError(f'AI 服务响应异常: HTTP {resp.status_code} {resp.text[:200]}')
                for raw_line in resp.iter_lines(decode_unicode=True):
                    _append_debug_log('response.raw_line', {
                        'trace_id': trace_id,
                        'line': raw_line
                    })
                    if not raw_line:
                        continue
                    line = raw_line.strip()
                    if line.startswith('data:'):
                        line = line[5:].strip()
                    if not line or line == '[DONE]':
                        continue
                    try:
                        data = json.loads(line)
                        _append_debug_log('response.parsed', {
                            'trace_id': trace_id,
                            'data': data
                        })
                    except json.JSONDecodeError:
                        continue
                    choices = data.get('choices') or []
                    if not choices:
                        continue
                    delta = choices[0].get('delta') or {}
                    chunk = delta.get('content')
                    if chunk:
                        _append_debug_log('response.chunk', {
                            'trace_id': trace_id,
                            'chunk': chunk
                        })
                        aggregated_output.append(chunk)
                        yield chunk
                final_text = ''.join(aggregated_output)
                _append_debug_log('response.complete', {
                    'trace_id': trace_id,
                    'aggregated_text': final_text,
                    'frontend_text': final_text
                })
                return
        except requests.RequestException as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(retry_delay)
                continue
            _append_debug_log('response.error', {
                'trace_id': trace_id,
                'error': str(exc),
                'aggregated_text': ''.join(aggregated_output)
            })
            raise AIServiceError(f'AI 服务调用失败: {exc}') from exc

    if last_error:
        _append_debug_log('response.error', {
            'trace_id': trace_id,
            'error': str(last_error)
        })
        raise AIServiceError(f'AI 服务调用失败: {last_error}')


def validate_provider_connection(provider: Dict, timeout: int = 15) -> Tuple[bool, str]:
    url = provider['base_url'].rstrip('/') + '/v1/chat/completions'
    headers = _build_headers(provider['api_key'])
    payload = {
        'model': provider['model'],
        'messages': [
            {'role': 'system', 'content': '你是一个健康检查助手。'},
            {'role': 'user', 'content': '这是一条连通性测试消息，请仅回复 OK。'}
        ],
        'temperature': 0,
        'max_tokens': 10,
        'stream': False
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        content = ''
        if data.get('choices'):
            content = (data['choices'][0].get('message') or {}).get('content', '')
        return True, content.strip() or '验证成功'
    except requests.RequestException as exc:
        return False, f'网络错误: {exc}'
    except ValueError as exc:
        return False, f'解析响应失败: {exc}'
