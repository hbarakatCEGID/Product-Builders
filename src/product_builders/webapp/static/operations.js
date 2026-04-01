// Operations dashboard — WebSocket terminal + form handling

const OPS_LOG = '[Product Builders / Operations]';

/**
 * Turn FastAPI `detail` (string | validation array | object) into readable text.
 */
function formatFastApiDetail(detail) {
  if (detail == null || detail === '') {
    return '';
  }
  if (typeof detail === 'string') {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === 'string') {
          return item;
        }
        if (item && typeof item === 'object' && 'msg' in item) {
          const loc = Array.isArray(item.loc) ? item.loc.filter(Boolean).join(' → ') : '';
          const type = item.type ? ` (${item.type})` : '';
          return loc ? `${loc}: ${item.msg}${type}` : `${item.msg}${type}`;
        }
        try {
          return JSON.stringify(item);
        } catch {
          return String(item);
        }
      })
      .join('\n');
  }
  if (typeof detail === 'object') {
    try {
      return JSON.stringify(detail, null, 2);
    } catch {
      return String(detail);
    }
  }
  return String(detail);
}

async function parseErrorResponse(resp, fallback) {
  const ct = (resp.headers.get('content-type') || '').toLowerCase();
  try {
    if (ct.includes('application/json')) {
      const d = await resp.json();
      const formatted = formatFastApiDetail(d.detail ?? d.message ?? d);
      return { text: formatted || fallback, raw: d };
    }
    const t = (await resp.text()).trim();
    return { text: t || fallback, raw: null };
  } catch {
    return { text: fallback, raw: null };
  }
}

function shellQuoteArg(arg) {
  const s = String(arg);
  if (/[\s"'\\]/.test(s)) {
    return JSON.stringify(s);
  }
  return s;
}

function formatCliArgv(argv) {
  if (!argv || !argv.length) {
    return '';
  }
  return argv.map(shellQuoteArg).join(' ');
}

function appendStderr(output, text) {
  const span = document.createElement('span');
  span.className = 'stderr';
  span.textContent = text.endsWith('\n') ? text : `${text}\n`;
  output.appendChild(span);
  output.scrollTop = output.scrollHeight;
}

function activateTab(btn) {
  document.querySelectorAll('.ops-tabs .tab').forEach((t) => t.classList.remove('active'));
  btn.classList.add('active');
}

function resetSubmitBtn(submitBtn) {
  if (!submitBtn) return;
  submitBtn.disabled = false;
  submitBtn.textContent = submitBtn.dataset.originalText || 'Run';
}

function setTerminalStatus(el, text, variant) {
  el.textContent = text;
  if (variant === 'success') {
    el.className = 'badge ok';
  } else if (variant === 'danger') {
    el.className = 'badge err';
  } else {
    el.className = 'badge warn';
  }
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
  setTerminalStatus(status, 'running', 'neutral');

  fetch(`/api/${command}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
    .then(async (resp) => {
      if (resp.status === 409) {
        const { text, raw } = await parseErrorResponse(
          resp,
          'A job is already running. Wait for it to finish.',
        );
        console.error(`${OPS_LOG} start_job conflict`, {
          command,
          httpStatus: 409,
          detail: text,
          raw,
        });
        throw new Error(text);
      }
      if (!resp.ok) {
        const { text, raw } = await parseErrorResponse(
          resp,
          `HTTP ${resp.status} ${resp.statusText || ''}`.trim(),
        );
        console.error(`${OPS_LOG} start_job rejected`, {
          command,
          httpStatus: resp.status,
          detail: text,
          raw,
        });
        throw new Error(text);
      }
      return resp.json();
    })
    .then((data) => {
      console.info(`${OPS_LOG} job started`, { command, job_id: data.job_id });
      connectWebSocket(data.job_id, submitBtn, command);
    })
    .catch((err) => {
      const message = err && err.message ? err.message : String(err);
      appendStderr(output, `Error: ${message}`);
      console.error(`${OPS_LOG} start_job error`, { command, message, error: err });
      setTerminalStatus(status, 'error', 'danger');
      resetSubmitBtn(submitBtn);
    });
}

function connectWebSocket(jobId, submitBtn, commandLabel) {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${protocol}//${location.host}/api/ws/execute?job_id=${jobId}`);
  const output = document.getElementById('terminal-output');
  const status = document.getElementById('terminal-status');
  let completedNormally = false;
  let hadStreamedLog = false;

  ws.onmessage = function (event) {
    let msg;
    try {
      msg = JSON.parse(event.data);
    } catch (e) {
      console.error(`${OPS_LOG} invalid WebSocket JSON`, {
        jobId,
        command: commandLabel,
        data: event.data,
        error: e,
      });
      appendStderr(output, 'Error: Invalid message from server (see browser console).');
      return;
    }

    if (msg.type === 'log') {
      hadStreamedLog = true;
      const span = document.createElement('span');
      span.textContent = `${msg.line}\n`;
      if (msg.stream === 'stderr') {
        span.className = 'stderr';
      }
      output.appendChild(span);
      output.scrollTop = output.scrollHeight;
    } else if (msg.type === 'done') {
      completedNormally = true;
      const isOk = msg.status === 'completed';
      if (!isOk) {
        const detailLines = ['--- Failure details ---'];
        if (msg.command) {
          detailLines.push(`Operation: ${msg.command}`);
        }
        if (commandLabel && commandLabel !== msg.command) {
          detailLines.push(`API route: ${commandLabel}`);
        }
        const cliLine = formatCliArgv(msg.cli_argv);
        if (cliLine) {
          detailLines.push(`CLI: ${cliLine}`);
        }
        if (msg.exit_code != null) {
          detailLines.push(`Exit code: ${msg.exit_code}`);
        }
        if (msg.error) {
          detailLines.push(`Runner error: ${msg.error}`);
        }
        detailLines.push('---');
        appendStderr(output, `${detailLines.join('\n')}\n`);

        console.error(`${OPS_LOG} job failed`, {
          jobId,
          command: msg.command,
          apiCommand: commandLabel,
          cli_argv: msg.cli_argv,
          cli_line: cliLine || undefined,
          exit_code: msg.exit_code,
          runner_error: msg.error,
          duration_s: msg.duration_s,
        });

        if (!hadStreamedLog) {
          appendStderr(
            output,
            'No CLI stdout/stderr was streamed. Run the CLI command above in a terminal for full logs, ' +
              'or confirm the repo path exists on the machine running the webapp.',
          );
        }
      } else {
        console.info(`${OPS_LOG} job completed`, {
          jobId,
          command: msg.command,
          duration_s: msg.duration_s,
        });
      }
      setTerminalStatus(
        status,
        isOk ? `completed (${msg.duration_s}s)` : 'failed',
        isOk ? 'success' : 'danger',
      );
      resetSubmitBtn(submitBtn);
    } else if (msg.type === 'error') {
      completedNormally = true;
      const text = `Error: ${msg.message}\n`;
      appendStderr(output, text.trimEnd());
      console.error(`${OPS_LOG} WebSocket server error`, { jobId, command: commandLabel, message: msg.message });
      setTerminalStatus(status, 'error', 'danger');
      resetSubmitBtn(submitBtn);
    }
  };

  ws.onerror = function (ev) {
    console.error(`${OPS_LOG} WebSocket transport error`, { jobId, command: commandLabel, event: ev });
    setTerminalStatus(status, 'connection error', 'danger');
    resetSubmitBtn(submitBtn);
  };

  ws.onclose = function (ev) {
    if (completedNormally) {
      return;
    }
    console.error(`${OPS_LOG} WebSocket closed before completion`, {
      jobId,
      command: commandLabel,
      code: ev.code,
      reason: ev.reason || '',
      wasClean: ev.wasClean,
    });
    appendStderr(
      output,
      `WebSocket closed unexpectedly (code ${ev.code}). Open the browser console (F12) for details.`,
    );
    setTerminalStatus(status, 'disconnected', 'danger');
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
