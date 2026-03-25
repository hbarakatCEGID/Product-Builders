// Operations dashboard — WebSocket terminal + form handling

function activateTab(btn) {
  document.querySelectorAll('.ops-tabs .tab').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
}

function resetSubmitBtn(submitBtn) {
  if (!submitBtn) return;
  submitBtn.disabled = false;
  submitBtn.textContent = submitBtn.dataset.originalText || 'Run';
}

function setTerminalStatus(el, text, ok) {
  el.textContent = text;
  el.className = ok ? 'badge ok' : 'badge warn';
}

function submitCommand(event, command) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const body = {};

  for (const [key, value] of formData.entries()) {
    if (form.querySelector(`[name="${key}"][type="checkbox"]`)) {
      body[key] = form.querySelector(`[name="${key}"]`).checked;
    } else if (value !== '') {
      body[key] = value;
    }
  }

  const submitBtn = form.querySelector('#submit-btn');
  if (submitBtn) {
    submitBtn.dataset.originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Running...';
  }

  const terminal = document.getElementById('terminal');
  const output = document.getElementById('terminal-output');
  const status = document.getElementById('terminal-status');
  terminal.style.display = 'block';
  output.textContent = '';
  setTerminalStatus(status, 'running', false);

  fetch(`/api/${command}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
    .then(resp => {
      if (resp.status === 409) {
        throw new Error('A job is already running. Wait for it to finish.');
      }
      if (!resp.ok) {
        return resp.json().then(d => { throw new Error(d.detail || 'Request failed'); });
      }
      return resp.json();
    })
    .then(data => {
      connectWebSocket(data.job_id, submitBtn);
    })
    .catch(err => {
      output.textContent = `Error: ${err.message}\n`;
      setTerminalStatus(status, 'error', false);
      resetSubmitBtn(submitBtn);
    });
}

function connectWebSocket(jobId, submitBtn) {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${location.host}/api/ws/execute?job_id=${jobId}`);
  const output = document.getElementById('terminal-output');
  const status = document.getElementById('terminal-status');

  ws.onmessage = function (event) {
    const msg = JSON.parse(event.data);

    if (msg.type === 'log') {
      const span = document.createElement('span');
      span.textContent = msg.line + '\n';
      if (msg.stream === 'stderr') {
        span.className = 'stderr';
      }
      output.appendChild(span);
      output.scrollTop = output.scrollHeight;
    } else if (msg.type === 'done') {
      const isOk = msg.status === 'completed';
      setTerminalStatus(status, isOk ? `completed (${msg.duration_s}s)` : 'failed', isOk);
      resetSubmitBtn(submitBtn);
    } else if (msg.type === 'error') {
      output.textContent += `Error: ${msg.message}\n`;
    }
  };

  ws.onerror = function () {
    setTerminalStatus(status, 'connection error', false);
    resetSubmitBtn(submitBtn);
  };
}

// Pre-select tab from URL params on load
document.addEventListener('DOMContentLoaded', function () {
  const params = new URLSearchParams(location.search);
  const cmd = params.get('command');
  if (cmd) {
    const tab = document.querySelector(`.tab[hx-get="/partials/form/${cmd}"]`);
    if (tab) tab.click();
  }

  const name = params.get('name');
  if (name) {
    setTimeout(() => {
      const nameInput = document.querySelector('#name');
      if (nameInput) nameInput.value = name;
    }, 200);
  }
});
