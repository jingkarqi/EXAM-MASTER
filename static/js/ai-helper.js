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
  const AURORA_ID = 'ai-aurora-overlay';
  const AURORA_PULSE_LAYER_ID = 'ai-aurora-pulse-layer';
  const OVERLAY_MIN_VISIBLE_MS = 1400;
  const OVERLAY_EXIT_FADE_MS = 900;
  let auraHideTimer = null;
  let overlayDeactivateTimer = null;

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

  function ensureAuroraOverlay() {
    let overlay = document.getElementById(AURORA_ID);
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = AURORA_ID;
      overlay.innerHTML = `
        <div class="ai-aurora__layer"></div>
        <div class="ai-aurora__layer"></div>
        <div class="ai-aurora__layer"></div>
        <div class="ai-aurora__edge ai-aurora__edge--top"></div>
        <div class="ai-aurora__edge ai-aurora__edge--right"></div>
        <div class="ai-aurora__edge ai-aurora__edge--bottom"></div>
        <div class="ai-aurora__edge ai-aurora__edge--left"></div>
      `;
      document.body.appendChild(overlay);
    }
    return overlay;
  }

  function ensurePulseLayer() {
    let layer = document.getElementById(AURORA_PULSE_LAYER_ID);
    if (!layer) {
      layer = document.createElement('div');
      layer.id = AURORA_PULSE_LAYER_ID;
      layer.setAttribute('aria-hidden', 'true');
      document.body.appendChild(layer);
    }
    return layer;
  }

  function activateAurora() {
    const overlay = ensureAuroraOverlay();
    if (auraHideTimer) {
      clearTimeout(auraHideTimer);
      auraHideTimer = null;
    }
    if (overlayDeactivateTimer) {
      clearTimeout(overlayDeactivateTimer);
      overlayDeactivateTimer = null;
    }
    overlay.classList.remove('active');
    overlay.classList.add('pulsing');
    overlay.classList.remove('exiting');
    state.overlayActivatedAt = null;
    state.pendingDeactivate = false;
    const pulse = document.createElement('span');
    pulse.className = 'ai-aurora__pulse';
    const rect = trigger ? trigger.getBoundingClientRect() : null;
    const centerX = rect ? rect.left + rect.width / 2 : window.innerWidth / 2;
    const centerY = rect ? rect.top + rect.height / 2 : window.innerHeight / 2;
    pulse.style.setProperty('--pulse-x', `${centerX}px`);
    pulse.style.setProperty('--pulse-y', `${centerY}px`);
    const pulseLayer = ensurePulseLayer();
    pulseLayer.appendChild(pulse);
    pulse.addEventListener('animationend', () => {
      overlay.classList.add('active');
      overlay.classList.remove('pulsing');
      state.overlayActivatedAt = performance.now();
      const shouldDeactivate = state.pendingDeactivate;
      state.pendingDeactivate = false;
      pulse.remove();
      if (pulseLayer && pulseLayer.childElementCount === 0) {
        pulseLayer.remove();
      }
      if (shouldDeactivate) {
        deactivateAurora();
      }
    }, { once: true });
  }

  function deactivateAurora() {
    const overlay = document.getElementById(AURORA_ID);
    if (!overlay) return;
    if (overlay.classList.contains('pulsing') && !state.overlayActivatedAt) {
      state.pendingDeactivate = true;
      return;
    }
    const hideOverlay = () => {
      overlay.classList.add('exiting');
      overlay.classList.remove('active');
      overlay.classList.remove('pulsing');
      overlayDeactivateTimer = null;
      auraHideTimer = window.setTimeout(() => {
        if (overlay.parentNode && !overlay.classList.contains('active')) {
          overlay.remove();
        }
      }, OVERLAY_EXIT_FADE_MS);
    };
    const elapsed = state.overlayActivatedAt
      ? performance.now() - state.overlayActivatedAt
      : OVERLAY_MIN_VISIBLE_MS;
    const delay = Math.max(0, OVERLAY_MIN_VISIBLE_MS - elapsed);
    if (delay > 0) {
      overlayDeactivateTimer = window.setTimeout(hideOverlay, delay);
    } else {
      hideOverlay();
    }
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
    activateAurora();

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
      deactivateAurora();
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
