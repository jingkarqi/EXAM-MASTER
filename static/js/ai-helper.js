(() => {
  if (window.__AI_HELPER_INITIALIZED__) {
    return;
  }
  window.__AI_HELPER_INITIALIZED__ = true;

  const sharedState = window.__AI_HELPER_STATE__ || { running: false, controller: null };
  window.__AI_HELPER_STATE__ = sharedState;

  const ctx = window.__AI_CONTEXT__;
  if (!ctx || !ctx.questionId) return;

  const trigger = document.querySelector('[data-ai-trigger]');
  const modal = document.querySelector('[data-ai-modal]');
  const statusEl = modal ? modal.querySelector('[data-ai-status]') : null;
  const statusText = modal ? modal.querySelector('[data-ai-status-text]') : null;
  const resultEl = modal ? modal.querySelector('[data-ai-result]') : null;
  const errorEl = modal ? modal.querySelector('[data-ai-error]') : null;
  const titleEl = modal ? modal.querySelector('[data-ai-title]') : null;
  const modeDescEl = modal ? modal.querySelector('[data-ai-mode-desc]') : null;
  const closeButtons = modal ? modal.querySelectorAll('[data-ai-close]') : [];

  if (!trigger || !modal) return;
  if (!ctx.enabled) return;

  const state = sharedState;

  const modeLabels = {
    hint: 'AI提示',
    analysis: 'AI解析'
  };

  function currentMode() {
    return ctx.hasSubmission ? 'analysis' : 'hint';
  }

  function openModal() {
    modal.hidden = false;
    modal.classList.add('active');
  }

  function closeModal() {
    modal.classList.remove('active');
    modal.hidden = true;
    if (state.controller) {
      state.controller.abort();
    }
    state.controller = null;
    state.running = false;
    if (trigger) {
      trigger.disabled = false;
    }
  }

  function setStatus(text, variant = 'loading') {
    if (!statusEl || !statusText) return;
    statusText.textContent = text;
    statusEl.dataset.state = variant;
  }

  function resetModal(mode) {
    if (resultEl) {
      resultEl.textContent = '';
    }
    if (errorEl) {
      errorEl.textContent = '';
      errorEl.classList.add('d-none');
    }
    if (titleEl) {
      titleEl.textContent = modeLabels[mode] || 'AI助手';
    }
    if (modeDescEl) {
      modeDescEl.textContent = mode === 'analysis'
        ? '解析将包含题目分析、错误点定位与知识点归纳。'
        : '提示仅提供解题思路，不会直接给出答案。';
    }
    setStatus('AI 正在思考，请稍候…', 'loading');
  }

  function appendChunk(text) {
    if (!resultEl || !text) return;
    resultEl.textContent += text;
  }

  function showError(message) {
    if (!errorEl) return;
    errorEl.textContent = message;
    errorEl.classList.remove('d-none');
    setStatus('生成失败', 'error');
  }

  async function requestAI(mode) {
    if (state.running) {
      return;
    }
    state.running = true;
    if (trigger) {
      trigger.disabled = true;
    }
    state.controller = new AbortController();
    resetModal(mode);

    try {
      const response = await fetch('/ai/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          mode,
          question_id: ctx.questionId,
          question_bank_id: ctx.questionBankId,
          user_answer: ctx.userAnswer || ''
        }),
        signal: state.controller.signal
      });

      if (!response.ok) {
        let message = 'AI 服务调用失败，请稍后重试。';
        try {
          const data = await response.json();
          if (data && data.error) {
            message = data.error;
          }
        } catch (err) {
          // ignore json parse error
        }
        throw new Error(message);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value || new Uint8Array(), { stream: true });
        appendChunk(chunk);
      }

      setStatus('生成完成', 'success');
      if (!resultEl.textContent.trim()) {
        appendChunk('（暂无返回内容）');
      }
    } catch (error) {
      if (state.controller && state.controller.signal.aborted) {
        setStatus('已取消生成', 'error');
      } else {
        showError(error.message || 'AI 服务暂不可用。');
      }
    } finally {
      if (state.controller) {
        state.controller = null;
      }
      state.running = false;
      if (trigger) {
        trigger.disabled = false;
      }
    }
  }

  trigger.addEventListener('click', () => {
    const mode = currentMode();
    openModal();
    requestAI(mode);
  });

  closeButtons.forEach(btn => {
    btn.addEventListener('click', () => closeModal());
  });

  modal.addEventListener('click', event => {
    if (event.target === modal) {
      closeModal();
    }
  });

  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && modal.classList.contains('active')) {
      closeModal();
    }
  });

  // 初始化按钮标签
  const labelEl = trigger.querySelector('[data-ai-label]');
  if (labelEl) {
    labelEl.textContent = ctx.hasSubmission ? 'AI解析' : 'AI提示';
  }
})();
