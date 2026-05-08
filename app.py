"""HTTP server + CLI entry for Wall Street Valuation Workbench."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from valuation_workbench import (
    Session, save_session as session_save, load_session as session_load, new_session,
    list_targets, get_schema, TARGET_LABELS,
    run_pipeline, to_markdown, to_json,
    render_tear_sheet, render_sensitivity_heatmap, render_scenario_comparison,
    CITATIONS,
)

REPO_ROOT = Path(__file__).resolve().parent
SESSION_CACHE: dict = {}


# ───────────────────────── Frontend (frontend-design skill) ──────────────────────────

STYLE_CSS = """
:root {
  --ink: #0b0e1f;
  --ink-2: #141937;
  --parchment: #f5ecd9;
  --parchment-2: #ece0c4;
  --amber: #ffb454;
  --amber-soft: #f7d8a3;
  --twilight: #7ec4cf;
  --rust: #c44536;
  --green: #16a34a;
  --rule: rgba(245,236,217,0.18);
  --rule-strong: rgba(245,236,217,0.42);
  --shadow-deep: 0 30px 80px -20px rgba(0,0,0,0.55);
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: 'JetBrains Mono', 'Noto Sans SC', ui-monospace, monospace;
  font-size: 14px; line-height: 1.6;
  color: var(--parchment); background: var(--ink);
  min-height: 100vh; position: relative; overflow-x: hidden;
}
.sky {
  position: fixed; inset: 0; z-index: -2; pointer-events: none;
  background:
    radial-gradient(ellipse 60% 45% at 12% 8%, rgba(255,180,84,0.15), transparent 60%),
    radial-gradient(ellipse 50% 40% at 88% 14%, rgba(126,196,207,0.13), transparent 65%),
    linear-gradient(180deg, #060818 0%, #0b0e1f 38%, #14122b 78%, #1a1430 100%);
}
.grain {
  position: fixed; inset: 0; z-index: -1; pointer-events: none; opacity: 0.06;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  mix-blend-mode: overlay;
}
header.topbar {
  display: flex; align-items: center; justify-content: space-between;
  max-width: 1200px; margin: 0 auto; padding: 22px 28px 8px;
}
header.topbar .brand {
  font-family: 'Fraunces', 'Noto Serif SC', serif;
  font-weight: 500; font-size: 22px; letter-spacing: -0.01em;
}
header.topbar .brand em { color: var(--amber); font-style: italic; font-weight: 400; }
header.topbar .stages {
  display: flex; gap: 6px; flex-wrap: wrap;
}
.stage-pill {
  padding: 6px 12px; font-family: 'JetBrains Mono', monospace; font-size: 11px;
  letter-spacing: 0.1em; color: rgba(245,236,217,0.5);
  border: 1px solid var(--rule); border-radius: 12px; background: rgba(11,14,31,0.4);
}
.stage-pill.active { color: var(--ink); background: var(--amber); border-color: var(--amber); }
.stage-pill.done { color: var(--twilight); border-color: var(--twilight); }
header.topbar .ctl {
  margin-left: 6px; padding: 6px 10px; font-size: 11px; font-family: 'JetBrains Mono', monospace;
  border: 1px dashed var(--rule-strong); border-radius: 2px;
  background: transparent; color: rgba(245,236,217,0.7); cursor: pointer;
}
header.topbar .ctl:hover { color: var(--amber); border-color: var(--amber); }
main { max-width: 1100px; margin: 0 auto; padding: 14px 28px 60px; }
h1 {
  font-family: 'Fraunces', 'Noto Serif SC', serif;
  font-weight: 300; font-size: clamp(40px, 6vw, 76px);
  line-height: 0.96; letter-spacing: -0.02em; margin: 24px 0 16px;
}
h1 em { font-style: italic; font-weight: 500; color: var(--amber); }
.eyebrow {
  font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase;
  color: var(--amber); opacity: 0.85; margin: 8px 0 18px;
}
.lede { max-width: 64ch; font-size: 14.5px; line-height: 1.7; color: rgba(245,236,217,0.78); }
.cite { color: var(--amber-soft); white-space: nowrap; }
.cards { display: grid; grid-template-columns: repeat(2, 1fr); gap: 18px; margin-top: 24px; }
.card {
  position: relative; display: block; padding: 26px 24px 56px;
  background: linear-gradient(160deg, rgba(245,236,217,0.06), rgba(245,236,217,0.02));
  border: 1px solid var(--rule); border-radius: 2px;
  text-decoration: none; color: var(--parchment);
  transition: transform 0.4s, border-color 0.3s, background 0.3s;
  overflow: hidden; min-height: 200px;
}
.card::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
  background: var(--amber); transform: scaleY(0.3); transform-origin: top; transition: transform 0.5s;
}
.card:hover { transform: translateY(-4px); border-color: var(--rule-strong); background: linear-gradient(160deg, rgba(255,180,84,0.07), rgba(245,236,217,0.03)); }
.card:hover::before { transform: scaleY(1); }
.card-glyph { position: absolute; top: 22px; right: 24px; font-size: 26px; color: var(--amber); }
.card-num { font-size: 10.5px; letter-spacing: 0.22em; color: var(--twilight); }
.card h3 {
  font-family: 'Fraunces', 'Noto Serif SC', serif; font-weight: 500;
  font-size: 23px; margin: 8px 0 8px; letter-spacing: -0.01em;
}
.card p { color: rgba(245,236,217,0.72); margin: 0; font-size: 13.5px; }
.card-arrow { position: absolute; bottom: 22px; right: 26px; color: var(--amber); font-size: 20px; transition: transform 0.3s; }
.card:hover .card-arrow { transform: translateX(6px); }
.card-2 { transform: translateY(14px); } .card-3 { transform: translateY(-6px); } .card-4 { transform: translateY(8px); }
.card-2:hover { transform: translateY(10px); } .card-3:hover { transform: translateY(-10px); } .card-4:hover { transform: translateY(4px); }
.section-label {
  font-family: 'Fraunces', 'Noto Serif SC', serif; font-weight: 300; font-style: italic;
  font-size: 21px; display: flex; align-items: baseline; gap: 14px;
  margin: 36px 0 18px; padding-bottom: 10px;
  border-bottom: 1px solid var(--rule);
}
.section-label .num {
  font-family: 'JetBrains Mono', monospace; font-style: normal;
  font-size: 11px; letter-spacing: 0.2em; color: var(--amber);
}
.field-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 24px; margin-bottom: 24px; }
.field {
  border: 1px solid var(--rule); border-radius: 2px;
  background: rgba(11,14,31,0.5);
  padding: 12px 16px;
}
.field label.fl {
  font-size: 12px; color: rgba(245,236,217,0.85); display: block; margin-bottom: 6px;
}
.field input[type=range] { width: 100%; accent-color: var(--amber); }
.field .vdisp { color: var(--amber); font-family: 'JetBrains Mono', monospace; font-size: 13px; margin-left: 8px; }
.field input[type=number], .field select, .field input[type=text] {
  width: 100%; font-family: 'JetBrains Mono', monospace; font-size: 13px;
  padding: 8px 10px; background: rgba(6,8,24,0.7); color: var(--parchment);
  border: 1px solid var(--rule); border-radius: 2px; outline: none;
}
.field input:focus, .field select:focus { border-color: var(--amber); box-shadow: 0 0 0 3px rgba(255,180,84,0.15); }
.field .multi-opts { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
.field .multi-opt {
  padding: 4px 10px; border: 1px solid var(--rule); border-radius: 12px;
  font-size: 11px; cursor: pointer; user-select: none;
}
.field .multi-opt.on { background: var(--amber); color: var(--ink); border-color: var(--amber); }
.btn {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 12px 22px;
  font-family: 'Fraunces', 'Noto Serif SC', serif; font-weight: 500; font-size: 15px;
  color: var(--ink); background: var(--amber);
  border: none; border-radius: 2px; cursor: pointer;
  box-shadow: var(--shadow-deep);
}
.btn:hover { background: #ffc274; transform: translateY(-1px); }
.btn-ghost {
  background: transparent; color: var(--amber);
  border: 1px solid var(--amber); padding: 8px 14px; font-size: 12px;
  font-family: 'JetBrains Mono', monospace;
}
.btn-ghost:hover { background: var(--amber); color: var(--ink); }
.tear-wrap {
  border: 1px solid var(--rule); border-radius: 2px;
  background: rgba(11,14,31,0.5); padding: 0; overflow: hidden;
  box-shadow: var(--shadow-deep); margin-bottom: 18px;
}
.tear-wrap svg { display: block; width: 100%; height: auto; }
.svg-card {
  border: 1px solid var(--rule); border-radius: 2px;
  background: rgba(11,14,31,0.4); padding: 14px; margin: 14px 0;
}
.svg-card svg { width: 100%; height: auto; }
.archetype-card {
  padding: 22px; border-left: 4px solid var(--amber);
  background: linear-gradient(120deg, rgba(255,180,84,0.08), rgba(245,236,217,0.03));
  border-radius: 2px; margin: 18px 0;
}
.archetype-card .arch-label {
  font-family: 'Fraunces', 'Noto Serif SC', serif; font-weight: 500;
  font-size: 26px; color: var(--amber); margin: 0 0 6px;
}
.archetype-card .arch-fit { font-size: 11px; color: var(--twilight); letter-spacing: 0.1em; }
.archetype-card .arch-desc { color: rgba(245,236,217,0.85); font-size: 14px; margin-top: 10px; }
.strategy-card {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin: 18px 0;
}
.strat-pill {
  padding: 14px; background: rgba(11,14,31,0.5);
  border: 1px solid var(--rule); border-radius: 2px; text-align: center;
}
.strat-pill .label { font-size: 10.5px; letter-spacing: 0.2em; color: var(--amber); }
.strat-pill .value {
  font-family: 'Fraunces', 'Noto Serif SC', serif; font-weight: 500;
  font-size: 22px; color: var(--parchment); margin-top: 6px;
}
.improvements ol { margin: 0; padding-left: 24px; }
.improvements li { margin-bottom: 8px; color: rgba(245,236,217,0.85); }
.cites { padding-left: 20px; color: rgba(245,236,217,0.6); font-size: 12px; }
.cites li { margin-bottom: 4px; }
.privacy-banner {
  margin: 24px 0; padding: 12px 18px;
  border: 1px dashed rgba(126,196,207,0.4); border-radius: 2px;
  color: var(--twilight); font-size: 12px; text-align: center;
}
.scenario-row {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 16px;
}
.scenario-pill {
  padding: 14px 16px; background: rgba(11,14,31,0.5);
  border: 1px solid var(--rule); border-radius: 2px;
}
.scenario-pill .name { color: var(--twilight); font-size: 11px; letter-spacing: 0.15em; }
.scenario-pill .vals { font-family: 'JetBrains Mono', monospace; font-size: 12px; margin-top: 6px; color: rgba(245,236,217,0.85); }
.toast {
  position: fixed; bottom: 24px; right: 24px;
  padding: 14px 20px; border-radius: 2px;
  background: var(--amber); color: var(--ink); font-weight: 500;
  box-shadow: var(--shadow-deep); z-index: 1000;
  animation: slidein 0.3s, fadeout 0.3s 2.7s forwards;
}
.toast.error { background: var(--rust); color: var(--parchment); }
@keyframes slidein { from { transform: translateY(40px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
@keyframes fadeout { to { opacity: 0; transform: translateY(20px); } }
footer {
  max-width: 1100px; margin: 0 auto; padding: 30px 28px 50px;
  color: rgba(245,236,217,0.4); font-size: 12px; text-align: center;
}
@media (max-width: 720px) {
  .cards { grid-template-columns: 1fr; }
  .field-grid { grid-template-columns: 1fr; }
  .strategy-card, .scenario-row { grid-template-columns: 1fr; }
  .card-2, .card-3, .card-4 { transform: none; }
}
@media (prefers-reduced-motion: reduce) {
  .card, .toast { animation: none !important; transition: none !important; }
}
"""

APP_JS = r"""
(function() {
  const STORAGE_KEY = 'valuation_workbench_session_v1';

  function getSession() {
    try {
      const v = localStorage.getItem(STORAGE_KEY);
      return v ? JSON.parse(v) : null;
    } catch (e) { return null; }
  }
  function saveSession(s) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); return true; }
    catch (e) { return false; }
  }
  function showToast(msg, type) {
    const div = document.createElement('div');
    div.className = 'toast' + (type === 'error' ? ' error' : '');
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 3000);
  }

  // Stage A: target picker stores selection
  document.querySelectorAll('[data-target]').forEach(el => {
    el.addEventListener('click', (e) => {
      const t = el.getAttribute('data-target');
      let s = getSession() || { version: '0.1.0', stage: 'A', target_type: '', answers: {}, scenarios: {bear:{},base:{},bull:{}}, forward_var: {}, lang: 'zh' };
      s.target_type = t;
      s.stage = 'B';
      saveSession(s);
    });
  });

  // Stage B: dynamic form auto-save
  const form = document.getElementById('answers-form');
  if (form) {
    function snapshot() {
      let s = getSession() || { version: '0.1.0', stage: 'B', target_type: '', answers: {}, scenarios: {bear:{},base:{},bull:{}}, forward_var: {}, lang: 'zh' };
      s.target_type = form.dataset.target || s.target_type;
      s.answers = readAnswers();
      s.stage = 'B';
      saveSession(s);
      // sync slider displays
      form.querySelectorAll('input[type=range]').forEach(r => {
        const d = document.getElementById(r.name + '-disp');
        if (d) d.textContent = r.value;
      });
    }
    function readAnswers() {
      const out = {};
      Array.from(form.elements).forEach(el => {
        if (!el.name) return;
        if (el.type === 'checkbox' || el.dataset.multi) {
          // multi: collect data-fid + data-val from .multi-opt.on
        } else if (el.tagName === 'INPUT' || el.tagName === 'SELECT') {
          out[el.name] = el.value;
        }
      });
      // multi-select chips
      form.querySelectorAll('[data-fid]').forEach(group => {
        const fid = group.getAttribute('data-fid');
        const vals = [];
        group.querySelectorAll('.multi-opt.on').forEach(opt => {
          vals.push(opt.getAttribute('data-val'));
        });
        out[fid] = vals;
      });
      return out;
    }
    Array.from(form.elements).forEach(el => {
      el.addEventListener('input', snapshot);
      el.addEventListener('change', snapshot);
    });
    form.querySelectorAll('.multi-opt').forEach(opt => {
      opt.addEventListener('click', (e) => {
        e.preventDefault();
        opt.classList.toggle('on');
        snapshot();
      });
    });
    // restore
    const s = getSession();
    if (s && s.answers) {
      Object.keys(s.answers).forEach(fid => {
        const v = s.answers[fid];
        const el = form.elements[fid];
        if (el) {
          if (Array.isArray(v)) {
            // multi
            const group = form.querySelector('[data-fid="' + fid + '"]');
            if (group) {
              v.forEach(val => {
                const opt = group.querySelector('[data-val="' + val + '"]');
                if (opt) opt.classList.add('on');
              });
            }
          } else {
            el.value = v;
          }
        } else {
          // multi
          const group = form.querySelector('[data-fid="' + fid + '"]');
          if (group && Array.isArray(v)) {
            v.forEach(val => {
              const opt = group.querySelector('[data-val="' + val + '"]');
              if (opt) opt.classList.add('on');
            });
          }
        }
      });
      // sync displays
      form.querySelectorAll('input[type=range]').forEach(r => {
        const d = document.getElementById(r.name + '-disp');
        if (d) d.textContent = r.value;
      });
    }
    // submit
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      snapshot();
      const ses = getSession();
      window.location.href = '/stage/c';
    });
  }

  // Stage C: forward variable + scenarios → trigger compute
  const formC = document.getElementById('forward-form');
  if (formC) {
    formC.addEventListener('submit', async (e) => {
      e.preventDefault();
      const ses = getSession();
      if (!ses || !ses.target_type) { showToast('请先选择估值对象', 'error'); return; }
      ses.forward_var = {
        id: formC.elements['forward_var_id']?.value || '',
        name: formC.elements['forward_var_name']?.value || '',
        delta_pct: parseFloat(formC.elements['delta_pct']?.value || '0.30'),
      };
      saveSession(ses);
      try {
        const r = await fetch('/api/compute', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({
            target_type: ses.target_type,
            answers: ses.answers,
            forward_var_id: ses.forward_var.id,
            forward_var_name: ses.forward_var.name,
            delta_pct: ses.forward_var.delta_pct,
          })
        });
        const data = await r.json();
        if (data.id) {
          ses.stage = 'D';
          saveSession(ses);
          window.location.href = '/results?id=' + encodeURIComponent(data.id);
        } else {
          showToast('计算失败: ' + JSON.stringify(data), 'error');
        }
      } catch(err) { showToast('网络错误: ' + err.message, 'error'); }
    });
  }

  // Top-bar session controls
  document.getElementById('btn-save')?.addEventListener('click', () => {
    const s = getSession() || {};
    const blob = new Blob([JSON.stringify(s, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'valuation-session-' + Date.now() + '.json'; a.click();
    URL.revokeObjectURL(url); showToast('已保存到下载目录');
  });
  document.getElementById('btn-load')?.addEventListener('click', () => {
    document.getElementById('file-load').click();
  });
  document.getElementById('file-load')?.addEventListener('change', async (e) => {
    const f = e.target.files[0]; if (!f) return;
    try {
      const obj = JSON.parse(await f.text());
      saveSession(obj);
      showToast('已恢复'); setTimeout(() => location.reload(), 800);
    } catch (err) { showToast('加载失败: ' + err.message, 'error'); }
  });
  document.getElementById('btn-reset')?.addEventListener('click', () => {
    if (confirm('清除当前会话?')) { localStorage.removeItem(STORAGE_KEY); location.href = '/'; }
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input, textarea, select')) return;
    if (e.key.toLowerCase() === 's') document.getElementById('btn-save')?.click();
    else if (e.key.toLowerCase() === 'l') document.getElementById('btn-load')?.click();
    else if (e.key.toLowerCase() === 'r') document.getElementById('btn-reset')?.click();
    else if (e.key.toLowerCase() === 'n') document.querySelector('[data-next-stage]')?.click();
    else if (e.key.toLowerCase() === 'p') document.querySelector('[data-prev-stage]')?.click();
  });
})();
"""

HEAD = """<!doctype html><html lang="{lang}"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,500;9..144,700&family=JetBrains+Mono:wght@400;600&family=Noto+Serif+SC:wght@400;500;700&family=Noto+Sans+SC:wght@400&display=swap"/>
<link rel="stylesheet" href="/static/style.css"/>
<script defer src="/static/app.js"></script>
</head><body><div class="sky"></div><div class="grain"></div>"""


def _topbar(stage: str = "A") -> str:
    stages = ["A", "B", "C", "D"]
    stage_label = {"A": "对象", "B": "问卷", "C": "前瞻", "D": "报告"}
    pills2 = []
    for s in stages:
        cls = "stage-pill"
        if s == stage:
            cls += " active"
        elif stages.index(s) < stages.index(stage):
            cls += " done"
        pills2.append(f'<span class="{cls}">{s} · {stage_label[s]}</span>')
    return f"""<header class="topbar">
<div class="brand"><span style="color:var(--amber)">$</span> Valuation <em>Workbench</em></div>
<div class="stages">{''.join(pills2)}</div>
<div>
<button class="ctl" id="btn-save" title="保存 (S)">💾 保存</button>
<button class="ctl" id="btn-load" title="加载 (L)">📂 加载</button>
<button class="ctl" id="btn-reset" title="重置 (R)">↺ 重置</button>
<input id="file-load" type="file" accept="application/json" style="display:none"/>
</div>
</header>"""


FOOTER = """<footer><p>Valuation Workbench · IB-grade metaphor · 本机运行 · 12+ 文献引用 · MIT</p></footer>
</body></html>"""


def _page(title: str, body: str, stage: str = "A", lang: str = "zh") -> str:
    return HEAD.format(lang=lang, title=title) + _topbar(stage) + body + FOOTER


HOME_BODY = """<main>
<p class="eyebrow">// 投行级估值方法 · 本地运行 · 12+ 文献引用</p>
<h1>给 <em>人</em> · <em>暧昧</em> · <em>感情</em><br/>做投行级估值</h1>
<p class="lede">用华尔街投行的方法 — <span class="cite">DCF</span>、<span class="cite">PE/PB/EPS</span>、<span class="cite">敏感性表</span>、<span class="cite">前瞻变量</span>、<span class="cite">投资策略建议</span> — 给一个人/暧昧对象/一段感情/你自己做估值。半严肃 meme 工具,不是财务建议,也不是心理咨询。</p>

<h2 class="section-label"><span class="num">A</span> 选择估值对象</h2>
<div class="cards">
  <a class="card card-1" href="/stage/b/person" data-target="person"><span class="card-glyph">👤</span><span class="card-num">/01</span><h3>给一个人估值</h3><p>朋友、同事、合作伙伴、刚介绍的相亲对象 — 任何你想 quick screen 的人。</p><span class="card-arrow">→</span></a>
  <a class="card card-2" href="/stage/b/crush" data-target="crush"><span class="card-glyph">💌</span><span class="card-num">/02</span><h3>给暧昧对象估值</h3><p>"TA 到底值不值得继续投入" 翻译成 PE/EPS/DCF 表。</p><span class="card-arrow">→</span></a>
  <a class="card card-3" href="/stage/b/relationship" data-target="relationship"><span class="card-glyph">💍</span><span class="card-num">/03</span><h3>给一段感情估值</h3><p>已经在一起的关系 — 评估维护成本、退出成本、增长对齐、forward step。</p><span class="card-arrow">→</span></a>
  <a class="card card-4" href="/stage/b/self" data-target="self"><span class="card-glyph">🧭</span><span class="card-num">/04</span><h3>给自己估值</h3><p>"我现在值多少" — 技能、人脉、增长率、可选性、健康。诚实自检。</p><span class="card-arrow">→</span></a>
</div>

<p class="privacy-banner">本机运行 · 不上传 · 不联网 · 所有数据保存在你浏览器的 localStorage</p>
</main>"""


def _render_field(field, lang: str = "zh") -> str:
    label = field.label_zh if lang == "zh" else field.label_en
    fid = field.id
    if field.kind == "slider":
        return f"""<div class="field">
<label class="fl">{label} <span class="vdisp" id="{fid}-disp">{field.default}</span></label>
<input type="range" name="{fid}" min="{field.min}" max="{field.max}" step="{field.step}" value="{field.default}"/>
</div>"""
    if field.kind == "number":
        return f"""<div class="field">
<label class="fl">{label}</label>
<input type="number" name="{fid}" min="{field.min}" max="{field.max}" step="{field.step}" value="{field.default}"/>
</div>"""
    if field.kind == "radio":
        opts = "".join(f'<option value="{o[0]}">{o[1] if lang=="zh" else o[2]}</option>' for o in field.options)
        return f"""<div class="field">
<label class="fl">{label}</label>
<select name="{fid}">{opts}</select>
</div>"""
    if field.kind == "multi":
        opts = "".join(f'<span class="multi-opt" data-val="{o[0]}">{o[1] if lang=="zh" else o[2]}</span>' for o in field.options)
        return f"""<div class="field">
<label class="fl">{label}</label>
<div class="multi-opts" data-fid="{fid}">{opts}</div>
</div>"""
    return ""


def _stage_b_body(target_type: str, lang: str = "zh") -> str:
    schema = get_schema(target_type)
    if not schema:
        return f"<main><p>Unknown target {target_type}</p></main>"
    fields_html = "".join(_render_field(f, lang) for f in schema.fields)
    label = schema.label_zh if lang == "zh" else schema.label_en
    desc = schema.description_zh if lang == "zh" else schema.description_en
    return f"""<main>
<p class="eyebrow"><a href="/" style="color:inherit">← 重选</a> · 估值对象: {label}</p>
<h1>{label}</h1>
<p class="lede">{desc}</p>
<form id="answers-form" data-target="{target_type}">
<h2 class="section-label"><span class="num">B</span> 填写问卷 (滑块/选择 — 自动保存)</h2>
<div class="field-grid">{fields_html}</div>
<button class="btn" type="submit" data-next-stage>下一步 · 前瞻变量 →</button>
</form>
</main>"""


def _stage_c_body(lang: str = "zh") -> str:
    return f"""<main>
<p class="eyebrow">阶段 C · 前瞻变量与三场景</p>
<h1>设定 <em>前瞻变量</em></h1>
<p class="lede">投行估值最重要的一步:挑出 1-2 个会显著影响未来 1 年估值的关键变量, 设定 bear / base / bull 三场景的扰动幅度。</p>
<form id="forward-form">
<h2 class="section-label"><span class="num">C1</span> 前瞻变量</h2>
<div class="field-grid">
  <div class="field">
    <label class="fl">前瞻变量名称 (你认为关键的事件)</label>
    <input type="text" name="forward_var_name" placeholder="如: TA 升职 / 我们见家长 / 异地变同城 / 我跳槽" value=""/>
  </div>
  <div class="field">
    <label class="fl">扰动幅度 (bear/bull 偏移基准 ±)</label>
    <input type="text" name="delta_pct" value="0.3" placeholder="0.3 表示 ±30%"/>
  </div>
  <div class="field">
    <label class="fl">绑定到字段(可选, 留空让系统自动选 forward_eligible 字段)</label>
    <input type="text" name="forward_var_id" placeholder="如: response_quality / growth_alignment"/>
  </div>
</div>
<button class="btn" type="submit">下一步 · 生成估值报告 →</button>
</form>
</main>"""


def _stage_d_body(report, rid: str, lang: str = "zh") -> str:
    tear_svg = render_tear_sheet(report)
    sens_svg = render_sensitivity_heatmap(report)
    scen_svg = render_scenario_comparison(report)
    if lang == "zh":
        rationale = report.strategy.rationale_zh
        improvements = report.strategy.improvements_zh
        arch_label = report.archetype.label_zh
        arch_desc = report.archetype.description_zh
    else:
        rationale = report.strategy.rationale_en
        improvements = report.strategy.improvements_en
        arch_label = report.archetype.label_en
        arch_desc = report.archetype.description_en

    imp_html = "".join(f"<li>{imp}</li>" for imp in improvements)
    cite_html = "".join(f"<li>{c}</li>" for c in report.citations)

    scenario_pills = ""
    for name, sc in report.scenarios.items():
        if isinstance(sc, dict) and "E" in sc:
            scenario_pills += f"""<div class="scenario-pill">
<div class="name">{name.upper()}</div>
<div class="vals">E: {sc['E']:.2f}<br/>g: {sc.get('g',0)*100:.1f}%<br/>WACC: {sc.get('wacc',0)*100:.1f}%</div>
</div>"""

    return f"""<main>
<p class="eyebrow">阶段 D · 估值报告 · session id {rid}</p>

<div class="tear-wrap">{tear_svg}</div>

<div class="archetype-card">
<div class="arch-fit">ARCHETYPE · 拟合度 {report.archetype.fit_score*100:.0f}%</div>
<p class="arch-label">{arch_label}</p>
<p class="arch-desc">{arch_desc}</p>
</div>

<div class="strategy-card">
<div class="strat-pill"><div class="label">POSITION</div><div class="value">{report.strategy.position}</div></div>
<div class="strat-pill"><div class="label">HOLD</div><div class="value">{report.strategy.hold_period}</div></div>
<div class="strat-pill"><div class="label">CONVICTION</div><div class="value">{report.strategy.conviction}</div></div>
</div>

<p class="lede" style="margin-top:8px">{rationale}</p>

<h2 class="section-label"><span class="num">01</span> 改进建议</h2>
<div class="improvements"><ol>{imp_html}</ol></div>

<h2 class="section-label"><span class="num">02</span> 三场景对比 (bear / base / bull)</h2>
<div class="scenario-row">{scenario_pills}</div>
<div class="svg-card">{scen_svg}</div>

<h2 class="section-label"><span class="num">03</span> 敏感性分析 (g × WACC)</h2>
<div class="svg-card">{sens_svg}</div>

<h2 class="section-label"><span class="num">04</span> 导出</h2>
<p>
<a class="btn-ghost" href="/export/{rid}.md?lang={lang}">↓ Markdown</a>
<a class="btn-ghost" href="/export/{rid}.json">↓ JSON</a>
<a class="btn-ghost" href="/" style="margin-left:14px">↻ 新建估值</a>
</p>

<h2 class="section-label"><span class="num">05</span> 文献引用</h2>
<ul class="cites">{cite_html}</ul>

<p class="privacy-banner">本估值基于 IB 方法的隐喻映射, 半严肃 meme 工具, 仅作参考, 非财务建议, 非心理咨询。</p>
</main>"""


# ───────────────────────── HTTP Handler ──────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        query = urllib.parse.parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}
        lang = query.get("lang", ["zh"])[0]

        if path == "/":
            self._html(_page("估值工作台 · Valuation Workbench", HOME_BODY, "A", lang)); return
        if path.startswith("/stage/b/"):
            target_type = path[len("/stage/b/"):]
            self._html(_page(f"问卷 · {target_type}", _stage_b_body(target_type, lang), "B", lang)); return
        if path == "/stage/c":
            self._html(_page("前瞻变量", _stage_c_body(lang), "C", lang)); return
        if path == "/results":
            rid = query.get("id", [""])[0]
            data = SESSION_CACHE.get(rid)
            if not data:
                self._html("<html><body><h1>结果已过期</h1><p><a href='/'>返回首页</a></p></body></html>", 404); return
            self._html(_page("估值报告", _stage_d_body(data["report"], rid, lang), "D", lang)); return
        if path == "/static/style.css":
            self._send(STYLE_CSS, "text/css; charset=utf-8"); return
        if path == "/static/app.js":
            self._send(APP_JS, "application/javascript; charset=utf-8"); return
        if path.startswith("/api/schema/"):
            target_type = path[len("/api/schema/"):]
            schema = get_schema(target_type)
            if not schema:
                self._json({"error": "unknown target"}, 404); return
            self._json(schema.to_dict()); return
        if path.startswith("/export/"):
            if path.endswith(".md"):
                rid = path[len("/export/"):-3]
                data = SESSION_CACHE.get(rid)
                if not data:
                    self._send("not found", "text/plain", 404); return
                self._send(to_markdown(data["report"], lang=lang), "text/markdown; charset=utf-8"); return
            if path.endswith(".json"):
                rid = path[len("/export/"):-5]
                data = SESSION_CACHE.get(rid)
                if not data:
                    self._send("not found", "text/plain", 404); return
                self._send(to_json(data["report"]), "application/json; charset=utf-8"); return
        self._send("not found", "text/plain", 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            self._json({"error": "invalid json"}, 400); return

        if self.path == "/api/compute":
            try:
                target_type = body.get("target_type")
                answers = body.get("answers") or {}
                forward_var_id = body.get("forward_var_id", "")
                forward_var_name = body.get("forward_var_name", "")
                delta_pct = float(body.get("delta_pct", 0.30))
                report = run_pipeline(target_type, answers, forward_var_id, forward_var_name, delta_pct)
                rid = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
                SESSION_CACHE[rid] = {"report": report}
                self._json({"id": rid})
            except Exception as e:
                self._json({"error": str(e)}, 400)
            return
        self._json({"error": "not found"}, 404)

    def _html(self, html: str, code: int = 200):
        self._send(html, "text/html; charset=utf-8", code)

    def _json(self, data, code: int = 200):
        self._send(json.dumps(data, ensure_ascii=False, default=str), "application/json; charset=utf-8", code)

    def _send(self, body, content_type: str, code: int = 200):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


def serve(host: str, port: int):
    server = HTTPServer((host, port), Handler)
    print(f"Valuation Workbench 运行于 http://{host}:{port}")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping..."); server.server_close()


def cli_main(args):
    target = args.target
    schema = get_schema(target)
    if not schema:
        print(f"Unknown target: {target}"); return
    answers = {}
    for f in schema.fields:
        answers[f.id] = f.default if not isinstance(f.default, list) else []
    report = run_pipeline(target, answers, args.forward_var_id or "", args.forward_var_name or "", args.delta_pct)
    if args.format == "json":
        out = to_json(report)
    else:
        out = to_markdown(report, lang=args.lang)
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8"); print(f"Wrote {args.out}")
    else:
        print(out)


def main():
    p = argparse.ArgumentParser(description="Wall Street Valuation Workbench")
    p.add_argument("--cli", action="store_true")
    p.add_argument("--target", default="crush", choices=list(list_targets()))
    p.add_argument("--forward-var-id", default="")
    p.add_argument("--forward-var-name", default="")
    p.add_argument("--delta-pct", type=float, default=0.30)
    p.add_argument("--lang", default="zh", choices=["zh", "en"])
    p.add_argument("--format", default="markdown", choices=["markdown", "json"])
    p.add_argument("--out")
    p.add_argument("--host", default=os.environ.get("VALUATION_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("VALUATION_PORT", "8782")))
    a = p.parse_args()
    if a.cli:
        cli_main(a)
    else:
        serve(a.host, a.port)


if __name__ == "__main__":
    main()
