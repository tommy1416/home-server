const API_URL = '/api/chat';
const MODELS_URL = '/api/models';
const DEFAULT_MODEL = 'gemma3n:e4b';

const state = { messages: [], pending: false, model: DEFAULT_MODEL };
const conversation = document.querySelector('#conversation');
const welcome = document.querySelector('#welcome');
const composer = document.querySelector('#composer');
const promptInput = document.querySelector('#prompt');
const sendButton = document.querySelector('#send-button');
const clearButton = document.querySelector('#clear-button');
const errorMessage = document.querySelector('#error-message');
const connectionStatus = document.querySelector('#connection-status');
const statusDot = document.querySelector('.status-dot');
const modelSelect = document.querySelector('#model-select');

function setStatus(label, kind = '') {
  connectionStatus.textContent = label;
  statusDot.className = `status-dot ${kind}`.trim();
}

function cleanContent(content) {
  // Strip Qwen-style <think>...</think> reasoning blocks for a clean chat view
  return String(content).replace(/<think>[\s\S]*?<\/think>/g, '').trim();
}

function renderMessage(role, content) {
  const message = document.createElement('article');
  message.className = `message ${role}`;
  const label = document.createElement('span');
  label.className = 'message-label';
  label.textContent = role === 'user' ? 'You' : 'AI';
  const body = document.createElement('div');
  body.className = 'message-body';
  body.textContent = cleanContent(content);
  message.append(label, body);
  conversation.append(message);
  conversation.parentElement.scrollTop = conversation.parentElement.scrollHeight;
  return body;
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
}

function clearError() {
  errorMessage.hidden = true;
  errorMessage.textContent = '';
}

function setPending(pending) {
  state.pending = pending;
  sendButton.disabled = pending;
  clearButton.disabled = pending;
  promptInput.disabled = pending;
  modelSelect.disabled = pending;
  sendButton.querySelector('span').textContent = pending ? 'Thinking' : 'Send';
  setStatus(pending ? 'Thinking' : 'Ready', pending ? 'busy' : '');
}

function resizeInput() {
  promptInput.style.height = 'auto';
  promptInput.style.height = `${Math.min(promptInput.scrollHeight, 180)}px`;
}

async function ask(question) {
  state.messages.push({ role: 'user', content: question });
  welcome.hidden = true;
  renderMessage('user', question);
  setPending(true);
  clearError();
  let failed = false;

  const aiBody = renderMessage('assistant', '');
  let full = '';

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ model: state.model, messages: state.messages, stream: true, keep_alive: '30m' }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => null);
      throw new Error(data?.error?.message || `Request failed (${response.status})`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        const payload = line.trim();
        if (!payload.startsWith('data:')) continue;
        const data = payload.slice(5).trim();
        if (!data || data === '[DONE]') continue;
        let chunk;
        try { chunk = JSON.parse(data); } catch { continue; }
        const delta = chunk?.choices?.[0]?.delta?.content;
        if (delta) { full += delta; aiBody.textContent = cleanContent(full); }
      }
    }
    if (!full) throw new Error('The AI returned an empty response.');
    state.messages.push({ role: 'assistant', content: full });
    aiBody.textContent = cleanContent(full);
  } catch (error) {
    failed = true;
    state.messages.pop();
    if (!full) aiBody.closest('article')?.remove();
    showError(error.message || 'Unable to reach the AI service.');
  } finally {
    setPending(false);
    if (failed) setStatus('Connection issue', 'error');
    promptInput.focus();
  }
}

async function loadModels() {
  try {
    const response = await fetch(MODELS_URL, { headers: { Accept: 'application/json' } });
    if (!response.ok) throw new Error(`Model discovery failed (${response.status})`);
    const data = await response.json();
    const models = (data.models || data.data || [])
      .map((model) => model.name || model.id)
      .filter(Boolean);
    if (!models.length) throw new Error('No models are available.');
    modelSelect.replaceChildren(...models.map((model) => new Option(model, model)));
    state.model = models.includes(DEFAULT_MODEL) ? DEFAULT_MODEL : models[0];
    modelSelect.value = state.model;
    modelSelect.disabled = false;
  } catch (error) {
    modelSelect.disabled = false;
    setStatus('Model list unavailable', 'error');
    showError(`${error.message} Using ${DEFAULT_MODEL}.`);
  }
}

composer.addEventListener('submit', (event) => {
  event.preventDefault();
  const question = promptInput.value.trim();
  if (!question || state.pending) return;
  promptInput.value = '';
  resizeInput();
  ask(question);
});

promptInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    composer.requestSubmit();
  }
});

promptInput.addEventListener('input', resizeInput);
clearButton.addEventListener('click', () => {
  state.messages = [];
  conversation.querySelectorAll('.message').forEach((message) => message.remove());
  welcome.hidden = false;
  clearError();
  setStatus('Ready');
  promptInput.focus();
});

document.querySelectorAll('[data-prompt]').forEach((button) => {
  button.addEventListener('click', () => {
    promptInput.value = button.dataset.prompt;
    resizeInput();
    promptInput.focus();
  });
});

modelSelect.addEventListener('change', () => {
  state.model = modelSelect.value;
  clearError();
  setStatus('Ready');
});

loadModels();
