/* ═══════════════════════════════════════════════════════════════════════════
   app.js — Amirreza Dorosti AI-Native Portfolio
   Frontend controller: Profile loading, Chat engine, Grounding Auditor (Idea 1)
   ═══════════════════════════════════════════════════════════════════════════ */

'use strict';

/* ── Config ─────────────────────────────────────────────────────────────────── */
const API_BASE = '';        // same origin — FastAPI serves both API and frontend
const ENDPOINTS = {
  profile : `${API_BASE}/api/profile`,
  chat    : `${API_BASE}/api/chat`,
};

/* ── State ──────────────────────────────────────────────────────────────────── */
let conversationHistory = [];   // [{role, content}, …]
let lastTrace           = null; // ExplainabilityTrace of the most recent turn

/* ── DOM refs ───────────────────────────────────────────────────────────────── */
const chatWindow        = document.getElementById('chat-window');
const chatInput         = document.getElementById('chat-input');
const sendBtn           = document.getElementById('send-btn');
const auditorOverlay    = document.getElementById('auditor-overlay');
const auditorClose      = document.getElementById('auditor-close');
const copyTraceBtn      = document.getElementById('copy-trace-btn');
const copyConfirm       = document.getElementById('copy-confirm');

/* ═══════════════════════════════════════════════════════════════════════════
   1. PROFILE LOADER — hydrate profile cards from GET /api/profile
   ═══════════════════════════════════════════════════════════════════════════ */
async function loadProfile() {
  try {
    const res = await fetch(ENDPOINTS.profile);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const profile = await res.json();
    renderCourses(profile.courses || []);
    renderProjects(profile.projects || []);
    renderJobFit(profile.job_fit_profile || {});
  } catch (err) {
    console.error('Profile load error:', err);
    ['courses-list','projects-list','jobfit-info'].forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.textContent = 'Could not load data.'; el.style.color = 'var(--red)'; }
    });
  }
}

function renderCourses(courses) {
  const el = document.getElementById('courses-list');
  if (!courses.length) { el.textContent = 'No courses listed.'; return; }
  el.innerHTML = courses.map(c => `
    <div class="course-item">
      <span class="course-code">${esc(c.code)}</span>
      <div class="course-title">${esc(c.title)}</div>
      <div class="course-term">${esc(c.term)}</div>
    </div>
  `).join('');
}

function renderProjects(projects) {
  const el = document.getElementById('projects-list');
  if (!projects.length) { el.textContent = 'No projects listed.'; return; }
  el.innerHTML = projects.map(p => `
    <div class="project-item">
      <div class="project-name">${esc(p.name)}</div>
      <div class="project-summary">${esc(p.summary)}</div>
      <div class="project-tags">
        ${(p.tech_stack || []).map(t => `<span class="tag">${esc(t)}</span>`).join('')}
      </div>
    </div>
  `).join('');
}

function renderJobFit(jf) {
  const el = document.getElementById('jobfit-info');
  const roles = (jf.target_roles || []).map(r => `<span class="tag">${esc(r)}</span>`).join('');
  const skills = (jf.core_competencies || []).map(s => `<div class="skill-item">${esc(s)}</div>`).join('');
  el.innerHTML = `
    <div style="margin-bottom:10px;display:flex;flex-wrap:wrap;gap:5px">${roles}</div>
    ${skills}
  `;
}

/* ═══════════════════════════════════════════════════════════════════════════
   2. CHAT ENGINE
   ═══════════════════════════════════════════════════════════════════════════ */
async function sendMessage(questionText) {
  const question = (questionText || chatInput.value).trim();
  if (!question) return;

  chatInput.value = '';
  sendBtn.disabled = true;

  appendMessage('user', question);
  const typingEl = appendTyping();

  try {
    const res = await fetch(ENDPOINTS.chat, {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify({ question, conversation_history: conversationHistory }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${res.status}`);
    }

    const data = await res.json();        // ChatResponse: {answer, trace}
    lastTrace = data.trace;

    // Defensively unwrap if answer ever contained raw JSON
    let cleanAnswer = data.answer || '';
    if (typeof cleanAnswer === 'string' && cleanAnswer.trim().startsWith('{')) {
      try {
        const parsed = JSON.parse(cleanAnswer);
        if (parsed.answer) cleanAnswer = parsed.answer;
      } catch (_) {
        const match = cleanAnswer.match(/"answer"\s*:\s*"((?:[^"\\]|\\.)*)"/);
        if (match) {
          cleanAnswer = match[1].replace(/\\"/g, '"').replace(/\\n/g, '\n');
        }
      }
    }

    typingEl.remove();
    appendMessage('assistant', cleanAnswer, data.trace);

    // Update conversation history for multi-turn
    conversationHistory.push({ role: 'user',      content: question });
    conversationHistory.push({ role: 'assistant', content: cleanAnswer });
    // Keep last 10 turns
    if (conversationHistory.length > 20) conversationHistory = conversationHistory.slice(-20);

  } catch (err) {
    typingEl.remove();
    appendError(err.message);
  } finally {
    sendBtn.disabled = false;
    chatInput.focus();
  }
}

/* ── Render helpers ─────────────────────────────────────────────────────────── */
function appendMessage(role, text, trace) {
  const div  = document.createElement('div');
  div.className = `msg msg--${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'msg__bubble';
  bubble.textContent = text;
  div.appendChild(bubble);

  if (role === 'assistant' && trace) {
    const meta = document.createElement('div');
    meta.className = 'msg__meta';

    const capClass = capabilityClass(trace.capability);
    meta.innerHTML = `
      <span class="cap-badge ${capClass}">${esc(trace.capability || '—')}</span>
      <span>${esc(trace.intent || '—')}</span>
    `;

    const audBtn = document.createElement('button');
    audBtn.className = 'auditor-btn';
    audBtn.textContent = '🔍 View Grounding Trace';
    audBtn.addEventListener('click', () => openAuditor(trace, text));
    meta.appendChild(audBtn);

    div.appendChild(meta);
  }

  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function appendTyping() {
  const div = document.createElement('div');
  div.className = 'msg msg--assistant';
  div.innerHTML = `
    <div class="typing-indicator">
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
      <div class="typing-dot"></div>
    </div>`;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return div;
}

function appendError(message) {
  const div = document.createElement('div');
  div.className = 'msg msg--assistant';
  div.innerHTML = `<div class="msg__bubble" style="border-color:var(--red);color:var(--red)">
    ⚠️ ${esc(message)}
  </div>`;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function capabilityClass(cap) {
  const map = {
    answer_from_record : 'cap-record',
    call_external_api  : 'cap-api',
    refuse_fact        : 'cap-refuse',
    ask_clarification  : 'cap-clarify',
    out_of_scope       : 'cap-scope',
  };
  return map[cap] || 'cap-record';
}

/* ═══════════════════════════════════════════════════════════════════════════
   3. GROUNDING AUDITOR (Idea 1 — Creative Feature)
   ═══════════════════════════════════════════════════════════════════════════ */
function openAuditor(trace, answerText) {
  lastTrace = trace;

  /* ── Intent / Capability badges ─────────────────────────────────────────── */
  document.getElementById('trace-intent').textContent     = `intent: ${trace.intent || '—'}`;
  document.getElementById('trace-capability').textContent = `capability: ${trace.capability || '—'}`;

  const apiEl = document.getElementById('trace-api');
  if (trace.external_service_used) {
    apiEl.textContent = `🔵 ${trace.external_service_used}`;
    apiEl.style.display = 'inline-block';
  } else {
    apiEl.style.display = 'none';
  }

  /* ── Fields read ─────────────────────────────────────────────────────────── */
  const fieldsList = document.getElementById('trace-fields');
  fieldsList.innerHTML = (trace.fields_read || [])
    .map(f => `<li>${esc(f)}</li>`)
    .join('') || '<li style="color:var(--text-muted)">None recorded</li>';

  /* ── Missing facts ───────────────────────────────────────────────────────── */
  const missingBlock = document.getElementById('missing-block');
  const missingList  = document.getElementById('trace-missing');
  if (trace.missing_facts && trace.missing_facts.length) {
    missingList.innerHTML = trace.missing_facts.map(m => `<li>${esc(m)}</li>`).join('');
    missingBlock.style.display = 'block';
  } else {
    missingBlock.style.display = 'none';
  }

  /* ── Audit spans ─────────────────────────────────────────────────────────── */
  const spansContainer = document.getElementById('trace-spans');
  const spans = trace.audit_spans || [];
  spansContainer.innerHTML = '';

  if (!spans.length) {
    spansContainer.innerHTML = '<p style="color:var(--text-muted);font-size:.82rem">No spans recorded.</p>';
  } else {
    // Legend
    const legend = document.createElement('div');
    legend.className = 'legend';
    legend.innerHTML = `
      <div class="legend-item"><div class="legend-dot" style="background:var(--green)"></div>record_grounded</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--blue)"></div>api_grounded</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--amber)"></div>missing_fact</div>
      <div class="legend-item"><div class="legend-dot" style="background:var(--red)"></div>guardrail_refusal</div>
    `;
    spansContainer.appendChild(legend);

    spans.forEach((span, idx) => {
      const card = document.createElement('div');
      card.className = 'span-card';
      card.dataset.idx = idx;

      const dotClass = spanDotClass(span.type);
      card.innerHTML = `
        <div class="span-dot ${dotClass}"></div>
        <div class="span-content">
          <div class="span-segment">"${esc(span.segment)}"</div>
          <div class="span-source">📍 ${esc(span.source)} · <em>${esc(span.type)}</em></div>
        </div>
      `;
      spansContainer.appendChild(card);
    });
  }

  /* ── Highlighted answer ──────────────────────────────────────────────────── */
  renderHighlightedAnswer(answerText, spans);

  /* ── Show overlay ────────────────────────────────────────────────────────── */
  auditorOverlay.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function renderHighlightedAnswer(answerText, spans) {
  const container = document.getElementById('trace-highlighted-answer');

  if (!spans || !spans.length) {
    container.textContent = answerText;
    return;
  }

  // Build highlighted HTML by replacing each matched segment with a colored span
  let html = esc(answerText);
  // Sort spans longest-first to avoid partial overwrites
  const sorted = [...spans].sort((a, b) => b.segment.length - a.segment.length);

  sorted.forEach(span => {
    const cls = highlightClass(span.type);
    const tooltip = `${span.source} (${span.type})`;
    // Escape the segment for use in a regex
    const escaped = escapeRegex(span.segment);
    const re = new RegExp(escapeRegex(esc(span.segment)), 'g');
    html = html.replace(re,
      `<mark class="${cls}" title="${esc(tooltip)}">${esc(span.segment)}</mark>`
    );
  });

  container.innerHTML = html;
}

function spanDotClass(type) {
  const map = {
    record_grounded  : 'span-dot--record',
    api_grounded     : 'span-dot--api',
    missing_fact_notice: 'span-dot--missing',
    guardrail_refusal: 'span-dot--refusal',
  };
  return map[type] || 'span-dot--record';
}

function highlightClass(type) {
  const map = {
    record_grounded    : 'highlight-record',
    api_grounded       : 'highlight-api',
    missing_fact_notice: 'highlight-missing',
    guardrail_refusal  : 'highlight-refusal',
  };
  return map[type] || 'highlight-record';
}

function closeAuditor() {
  auditorOverlay.classList.add('hidden');
  document.body.style.overflow = '';
}

/* ═══════════════════════════════════════════════════════════════════════════
   4. COPY TRACE — formats a clean markdown block for the submission report
   ═══════════════════════════════════════════════════════════════════════════ */
function buildMarkdownTrace(trace, answerText) {
  if (!trace) return '(No trace available)';

  const fields   = (trace.fields_read    || []).map(f => `  - ${f}`).join('\n') || '  - (none)';
  const missing  = (trace.missing_facts  || []).map(m => `  - ⚠️ ${m}`).join('\n') || '  - (none)';
  const api      = trace.external_service_used || 'null';

  const spans = (trace.audit_spans || []).map(s =>
    `  | ${spanEmoji(s.type)} ${s.type.padEnd(22)} | ${s.source.padEnd(45)} | "${s.segment.slice(0,60)}${s.segment.length>60?'…':''}"`
  ).join('\n');

  return `### Explainability Trace

**Intent:**    ${trace.intent}
**Capability:** ${trace.capability}
**External API:** ${api}

**Fields Read:**
${fields}

**Missing Facts:**
${missing}

**Audit Spans:**
  | Type                   | Source                                                       | Segment (truncated)
  |------------------------|--------------------------------------------------------------|---------------------
${spans}

**Answer:**
> ${(answerText || '').replace(/\n/g, '\n> ')}
`;
}

function spanEmoji(type) {
  return { record_grounded:'🟢', api_grounded:'🔵', missing_fact_notice:'🟠', guardrail_refusal:'🔴' }[type] || '⬜';
}

/* ═══════════════════════════════════════════════════════════════════════════
   5. EVENT LISTENERS
   ═══════════════════════════════════════════════════════════════════════════ */

// Send button
sendBtn.addEventListener('click', () => sendMessage());

// Enter key
chatInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

// Quick-prompt chips
document.querySelectorAll('.chip').forEach(chip => {
  chip.addEventListener('click', () => sendMessage(chip.dataset.q));
});

// Close auditor
auditorClose.addEventListener('click', closeAuditor);
auditorOverlay.addEventListener('click', e => {
  if (e.target === auditorOverlay) closeAuditor();
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeAuditor();
});

// Copy trace
copyTraceBtn.addEventListener('click', () => {
  if (!lastTrace) return;
  // Find the last assistant answer
  const bubbles = chatWindow.querySelectorAll('.msg--assistant .msg__bubble');
  const lastAnswer = bubbles.length ? bubbles[bubbles.length - 1].textContent : '';
  const md = buildMarkdownTrace(lastTrace, lastAnswer);
  navigator.clipboard.writeText(md).then(() => {
    copyConfirm.classList.remove('hidden');
    setTimeout(() => copyConfirm.classList.add('hidden'), 2500);
  }).catch(() => {
    // Fallback for non-HTTPS
    const ta = document.createElement('textarea');
    ta.value = md;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
    copyConfirm.classList.remove('hidden');
    setTimeout(() => copyConfirm.classList.add('hidden'), 2500);
  });
});

/* ═══════════════════════════════════════════════════════════════════════════
   6. UTILITIES
   ═══════════════════════════════════════════════════════════════════════════ */
function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/* ═══════════════════════════════════════════════════════════════════════════
   7. INIT
   ═══════════════════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  loadProfile();
  chatInput.focus();
});
