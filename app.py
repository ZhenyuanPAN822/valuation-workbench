"""HTTP server + CLI for 对象/暧昧估值工作台 v0.3 (light theme · 6-stage · LLM-driven)."""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from valuation_workbench import (
    list_targets, get_schema,
    run_pipeline, run_pipeline_ib, to_markdown, to_json,
    render_tear_sheet, render_sensitivity_heatmap, render_scenario_comparison,
    CITATIONS,
    get_fallback_schema, parse_dyn_schema,
    call_llm, PROVIDERS, ProviderError, probe_connection,
    parse_llm_json, ParseError,
    build_schema_prompt, FALLBACK_SCHEMA,
    build_forward_prompt, FALLBACK_FORWARD,
    schema_to_summary, answers_to_summary, ib_to_summary,
    build_narrative_prompt, fallback_narrative,
    valuation_to_summary, archetype_to_summary, forward_to_summary,
    aggregate_ib_inputs,
)

REPO_ROOT = Path(__file__).resolve().parent
SESSION_CACHE: dict = {}
SCHEMA_CACHE: dict = {}


# ───────────────────────── Light-theme CSS ─────────────────────────

STYLE_CSS = r"""
:root {
  --bg: #faf6ec;
  --bg-2: #f3ecda;
  --paper: #ffffff;
  --paper-2: #fffaf0;
  --ink: #1c2027;
  --ink-2: #424857;
  --ink-3: #6b7280;
  --rust: #c4632a;
  --rust-soft: #e89968;
  --teal: #2c5d6b;
  --green: #2f7d4f;
  --gold: #b8860b;
  --rule: rgba(28,32,39,0.10);
  --rule-strong: rgba(28,32,39,0.22);
  --shadow: 0 1px 2px rgba(28,32,39,0.04), 0 8px 24px -8px rgba(28,32,39,0.10);
  --shadow-deep: 0 4px 16px rgba(28,32,39,0.08), 0 30px 60px -20px rgba(28,32,39,0.20);
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: 'Noto Sans SC', system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 17px; line-height: 1.7;
  color: var(--ink); background: var(--bg);
  min-height: 100vh; -webkit-font-smoothing: antialiased;
  position: relative;
}
body::before {
  content: ""; position: fixed; inset: 0; z-index: -2; pointer-events: none;
  background:
    radial-gradient(ellipse 50% 35% at 12% 6%, rgba(196,99,42,0.08), transparent 60%),
    radial-gradient(ellipse 45% 35% at 88% 92%, rgba(44,93,107,0.06), transparent 65%);
}
body::after {
  content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none; opacity: 0.04;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
  mix-blend-mode: multiply;
}
@keyframes rise-in { from { opacity: 0; transform: translateY(12px); } to { opacity: 1; transform: translateY(0); } }
main > * { animation: rise-in 0.5s ease-out backwards; }
main > *:nth-child(1) { animation-delay: 0.04s; }
main > *:nth-child(2) { animation-delay: 0.10s; }
main > *:nth-child(3) { animation-delay: 0.16s; }
main > *:nth-child(4) { animation-delay: 0.22s; }
main > *:nth-child(5) { animation-delay: 0.28s; }
main > *:nth-child(6) { animation-delay: 0.34s; }
main > *:nth-child(n+7) { animation-delay: 0.40s; }
@media (prefers-reduced-motion: reduce) {
  main > * { animation: none; }
}
header.topbar {
  display: flex; align-items: center; gap: 14px;
  max-width: 1320px; margin: 0 auto; padding: 18px 28px 10px;
  flex-wrap: nowrap; overflow: hidden;
}
header.topbar .brand {
  font-family: 'Fraunces','Noto Serif SC', serif;
  font-weight: 500; font-size: 21px; letter-spacing: -0.01em;
  white-space: nowrap; flex-shrink: 0;
}
header.topbar .brand em { color: var(--rust); font-style: italic; font-weight: 500; }
header.topbar .brand .dot { color: var(--rust); margin-right: 4px; }
header.topbar .stages {
  display: flex; gap: 4px; flex-wrap: nowrap;
  flex: 1; min-width: 0; justify-content: center;
  overflow-x: auto; scrollbar-width: none;
}
header.topbar .stages::-webkit-scrollbar { display: none; }
.stage-pill {
  padding: 5px 9px; font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 11px;
  letter-spacing: 0.04em; color: var(--ink-3);
  border: 1px solid var(--rule); border-radius: 999px; background: var(--paper);
  white-space: nowrap; flex: 0 0 auto; line-height: 1.4;
}
.stage-pill.active { color: var(--paper); background: var(--rust); border-color: var(--rust); }
.stage-pill.done { color: var(--teal); border-color: var(--teal); }
header.topbar .ctls { display: flex; gap: 6px; flex-wrap: nowrap; flex-shrink: 0; }
header.topbar .ctl {
  padding: 6px 11px; font-size: 12px;
  border: 1px solid var(--rule); border-radius: 6px;
  background: var(--paper); color: var(--ink-2); cursor: pointer;
  white-space: nowrap;
}
header.topbar .ctl:hover { color: var(--rust); border-color: var(--rust); }
@media (max-width: 920px) {
  header.topbar { flex-wrap: wrap; overflow: visible; }
  header.topbar .stages { order: 3; flex-basis: 100%; justify-content: flex-start; padding-top: 4px; }
}
main { max-width: 1100px; margin: 0 auto; padding: 14px 36px 80px; }
h1 {
  font-family: 'Fraunces','Noto Serif SC', serif;
  font-weight: 400; font-size: clamp(40px, 6vw, 72px);
  line-height: 1.05; letter-spacing: -0.02em; margin: 28px 0 18px; color: var(--ink);
}
h1 em { font-style: italic; font-weight: 500; color: var(--rust); }
h2 {
  font-family: 'Fraunces','Noto Serif SC', serif;
  font-weight: 500; font-size: 30px; line-height: 1.2; margin: 28px 0 14px; color: var(--ink);
}
h3 {
  font-family: 'Fraunces','Noto Serif SC', serif;
  font-weight: 500; font-size: 22px; margin: 18px 0 10px; color: var(--ink);
}
.eyebrow {
  font-size: 13px; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--rust); font-weight: 600; margin: 8px 0 14px;
}
.lede {
  max-width: 64ch; font-size: 18px; line-height: 1.75; color: var(--ink-2);
}
.section-label {
  font-family: 'Fraunces','Noto Serif SC', serif; font-weight: 500;
  font-size: 26px; display: flex; align-items: baseline; gap: 14px;
  margin: 40px 0 18px; padding-bottom: 12px;
  border-bottom: 1px solid var(--rule); color: var(--ink);
}
.section-label .num {
  font-family: 'JetBrains Mono', ui-monospace, monospace; font-style: normal;
  font-size: 13px; letter-spacing: 0.18em; color: var(--rust);
}
.card {
  background: var(--paper); border: 1px solid var(--rule); border-radius: 10px;
  padding: 22px 26px; margin: 14px 0; box-shadow: var(--shadow);
}
.card.subtle {
  background: var(--bg-2); border-style: dashed;
}
.field {
  background: var(--paper); border: 1px solid var(--rule); border-radius: 8px;
  padding: 18px 20px; margin-bottom: 14px;
}
.field label.fl {
  font-size: 17px; color: var(--ink); display: block; margin-bottom: 8px; font-weight: 500;
}
.field .hint {
  font-size: 14px; color: var(--ink-3); margin-top: 8px; line-height: 1.55;
}
.field .anchors {
  display: flex; justify-content: space-between; gap: 12px;
  font-size: 13px; color: var(--ink-2); margin-top: 4px; margin-bottom: 6px;
}
.field .anchors .lo, .field .anchors .hi {
  background: var(--bg-2); padding: 4px 10px; border-radius: 4px; max-width: 48%;
}
.field input[type=range] {
  width: 100%; accent-color: var(--rust); height: 28px;
}
.field .vdisp {
  color: var(--rust); font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 17px; font-weight: 600; margin-left: 8px;
}
.field input[type=number], .field input[type=text], .field input[type=password], .field select, .field textarea {
  width: 100%; font-size: 16px; padding: 12px 14px;
  background: var(--paper); color: var(--ink);
  border: 1px solid var(--rule); border-radius: 6px; outline: none;
  font-family: inherit;
}
.field input:focus, .field select:focus, .field textarea:focus {
  border-color: var(--rust); box-shadow: 0 0 0 3px rgba(196,99,42,0.15);
}

/* Custom dropdown — replaces native <select> to avoid browser/OS rendering bugs */
.cdrop { position: relative; width: 100%; }
.cdrop-trigger {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; padding: 12px 14px; font-size: 16px; font-family: inherit;
  color: var(--ink); background: var(--paper);
  border: 1px solid var(--rule); border-radius: 6px;
  cursor: pointer; text-align: left;
}
.cdrop-trigger:hover { border-color: var(--rust-soft); }
.cdrop.open .cdrop-trigger { border-color: var(--rust); box-shadow: 0 0 0 3px rgba(196,99,42,0.15); }
.cdrop-trigger .arrow { color: var(--ink-3); margin-left: 10px; transition: transform 0.15s; }
.cdrop.open .cdrop-trigger .arrow { transform: rotate(180deg); color: var(--rust); }
.cdrop-menu {
  position: absolute; top: calc(100% + 4px); left: 0; right: 0; z-index: 9999;
  background: var(--paper); border: 1px solid var(--rule); border-radius: 8px;
  box-shadow: 0 10px 30px -8px rgba(28,32,39,0.18), 0 4px 8px rgba(28,32,39,0.06);
  list-style: none; margin: 0; padding: 6px 0;
  max-height: 320px; overflow-y: auto; display: none;
}
.cdrop.open .cdrop-menu { display: block; animation: cdrop-in 0.16s ease-out; }
@keyframes cdrop-in { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
.cdrop-menu li {
  padding: 11px 16px; cursor: pointer; color: var(--ink); font-size: 15px;
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
}
.cdrop-menu li:hover { background: var(--bg-2); color: var(--rust); }
.cdrop-menu li.on { background: rgba(196,99,42,0.08); color: var(--rust); font-weight: 600; }
.cdrop-menu li.on::after { content: '✓'; }
.cdrop-menu li.divider { padding: 0; height: 1px; background: var(--rule); margin: 4px 0; pointer-events: none; }
.cdrop-menu li.custom-opt { color: var(--rust); font-style: italic; }
.cdrop-menu li.custom-opt:hover { background: rgba(196,99,42,0.08); }
.likert-row { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 4px; }
.likert-opt {
  flex: 1; min-width: 56px; padding: 12px 8px; border: 1px solid var(--rule);
  border-radius: 8px; background: var(--paper); cursor: pointer;
  font-size: 16px; font-weight: 600; color: var(--ink-2); text-align: center;
  transition: all 0.15s;
}
.likert-opt:hover { border-color: var(--rust); color: var(--rust); }
.likert-opt.on { background: var(--rust); color: var(--paper); border-color: var(--rust); }
.btn {
  display: inline-flex; align-items: center; gap: 10px;
  padding: 14px 28px; font-size: 17px; font-weight: 600;
  color: var(--paper); background: var(--rust);
  border: none; border-radius: 8px; cursor: pointer;
  font-family: inherit; box-shadow: var(--shadow);
}
.btn:hover { background: #a8531e; transform: translateY(-1px); }
.btn[disabled] { opacity: 0.5; cursor: not-allowed; }
.btn-ghost {
  background: var(--paper); color: var(--rust);
  border: 1px solid var(--rust); padding: 10px 18px; font-size: 14px;
}
.btn-ghost:hover { background: var(--rust); color: var(--paper); }
.btn-secondary {
  background: var(--paper); color: var(--ink); border: 1px solid var(--rule);
}
.btn-secondary:hover { border-color: var(--ink); }
.toast {
  position: fixed; bottom: 28px; right: 28px;
  padding: 16px 24px; border-radius: 8px;
  background: var(--ink); color: var(--paper); font-size: 15px;
  box-shadow: var(--shadow-deep); z-index: 1000;
  animation: slidein 0.25s ease-out, fadeout 0.3s 3.2s forwards;
}
.toast.success { background: var(--green); }
.toast.error { background: #b54040; }
@keyframes slidein { from { transform: translateY(40px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
@keyframes fadeout { to { opacity: 0; transform: translateY(20px); } }
footer {
  max-width: 1100px; margin: 0 auto; padding: 40px 36px 60px;
  color: var(--ink-3); font-size: 14px; text-align: center;
  border-top: 1px solid var(--rule); margin-top: 40px;
}
.provider-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 14px 18px; }
textarea.bigdesc {
  min-height: 160px; resize: vertical; font-size: 16px; line-height: 1.7;
}
.spinner {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,0.4); border-top-color: var(--paper);
  border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: middle;
}
@keyframes spin { to { transform: rotate(360deg); } }
.history-list { display: flex; flex-direction: column; gap: 10px; margin-top: 14px; }
.history-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; background: var(--paper); border: 1px solid var(--rule);
  border-radius: 8px; gap: 14px;
}
.history-item .desc { flex: 1; font-size: 15px; color: var(--ink); }
.history-item .meta { font-size: 13px; color: var(--ink-3); white-space: nowrap; }
.history-item .actions { display: flex; gap: 8px; }
.subtheme-card {
  background: var(--bg-2); border-left: 3px solid var(--rust);
  padding: 18px 22px; border-radius: 8px; margin: 18px 0 14px;
}
.subtheme-card h3 { margin: 0 0 6px; font-size: 19px; }
.subtheme-card p { margin: 0; color: var(--ink-2); font-size: 14.5px; line-height: 1.6; }
.stage-why {
  background: linear-gradient(180deg, var(--bg-2), var(--paper));
  padding: 18px 22px; border-radius: 8px; border: 1px solid var(--rule);
  margin: 14px 0 22px;
}
.stage-why .lbl { color: var(--rust); font-weight: 600; font-size: 13px; letter-spacing: 0.1em; text-transform: uppercase; }
.stage-why p { margin: 8px 0 0; color: var(--ink-2); font-size: 15.5px; line-height: 1.65; }
.fair-row { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; margin: 14px 0 22px; }
.fair-cell {
  padding: 22px; background: var(--paper); border: 1px solid var(--rule); border-radius: 10px;
  text-align: center;
}
.fair-cell.mid {
  background: linear-gradient(180deg, var(--paper-2), var(--paper));
  border-color: var(--rust);
}
.fair-cell .lbl { font-size: 12px; letter-spacing: 0.18em; color: var(--ink-3); }
.fair-cell .val {
  font-family: 'Fraunces','Noto Serif SC', serif; font-size: 38px; font-weight: 500;
  color: var(--ink); margin-top: 6px;
}
.fair-cell.mid .val { color: var(--rust); font-size: 44px; }
.method-row { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; margin: 10px 0 18px; }
.method-cell { padding: 16px 18px; background: var(--bg-2); border: 1px dashed var(--rule); border-radius: 8px; }
.method-cell .lbl { font-size: 12px; color: var(--rust); font-weight: 600; letter-spacing: 0.08em; }
.method-cell .val { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 22px; margin-top: 4px; color: var(--ink); }
.method-cell .w { font-size: 12px; color: var(--ink-3); margin-top: 4px; }
.archetype-card {
  padding: 22px 26px; background: var(--paper); border: 1px solid var(--rule);
  border-left: 4px solid var(--rust); border-radius: 10px; margin: 18px 0;
}
.archetype-card .arch-fit { font-size: 12px; color: var(--teal); letter-spacing: 0.1em; }
.archetype-card .arch-label {
  font-family: 'Fraunces','Noto Serif SC', serif; font-weight: 500;
  font-size: 28px; color: var(--rust); margin: 6px 0 8px;
}
.archetype-card .arch-desc { color: var(--ink-2); font-size: 15.5px; }
.strategy-card { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; margin: 18px 0; }
.strat-pill {
  padding: 18px; background: var(--paper); border: 1px solid var(--rule);
  border-radius: 8px; text-align: center;
}
.strat-pill .label { font-size: 12px; letter-spacing: 0.18em; color: var(--rust); font-weight: 600; }
.strat-pill .value {
  font-family: 'Fraunces','Noto Serif SC', serif; font-weight: 500;
  font-size: 26px; color: var(--ink); margin-top: 8px;
}
.scenario-row { display: grid; grid-template-columns: repeat(3,1fr); gap: 14px; margin-bottom: 16px; }
.scenario-pill {
  padding: 16px 18px; background: var(--paper); border: 1px solid var(--rule);
  border-radius: 8px;
}
.scenario-pill .name { color: var(--rust); font-size: 12px; font-weight: 600; letter-spacing: 0.12em; }
.scenario-pill .vals { font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 13.5px; margin-top: 8px; color: var(--ink-2); }
.warnings {
  padding: 14px 20px; border: 1px dashed var(--rust); border-radius: 8px;
  color: var(--rust); margin: 14px 0; background: var(--paper-2); font-size: 14px;
}
.tear-wrap {
  border: 1px solid var(--rule); border-radius: 10px;
  background: var(--paper); overflow: hidden; box-shadow: var(--shadow);
  margin-bottom: 18px;
}
.tear-wrap svg, .svg-card svg { display: block; width: 100%; height: auto; background: var(--paper); }
.svg-card {
  border: 1px solid var(--rule); border-radius: 10px;
  background: var(--paper); padding: 16px; margin: 14px 0; box-shadow: var(--shadow);
}
.privacy-banner {
  margin: 20px 0; padding: 14px 18px;
  border: 1px dashed var(--teal); border-radius: 8px;
  color: var(--teal); font-size: 13.5px; text-align: center; background: var(--paper);
}
.test-result {
  display: inline-block; margin-left: 12px; padding: 6px 12px; border-radius: 6px;
  font-size: 13px; font-weight: 500; vertical-align: middle;
}
.test-result.ok { background: rgba(47,125,79,0.12); color: var(--green); }
.test-result.fail { background: rgba(181,64,64,0.12); color: #b54040; }
.thesis-block {
  background: var(--paper); border: 1px solid var(--rule); border-left: 4px solid var(--rust);
  padding: 22px 26px; border-radius: 8px; margin: 18px 0;
  font-size: 16.5px; line-height: 1.85; color: var(--ink);
}
.scenario-narrative { margin: 12px 0; padding: 16px 20px; background: var(--bg-2); border-radius: 8px; }
.scenario-narrative .h { color: var(--rust); font-weight: 600; font-size: 14px; letter-spacing: 0.08em; }
.scenario-narrative p { margin: 6px 0 0; color: var(--ink-2); }
.risk-card {
  background: var(--paper); border: 1px solid var(--rule); border-radius: 8px;
  padding: 16px 20px; margin: 10px 0;
}
.risk-card .h { font-weight: 600; color: var(--rust); margin-bottom: 6px; font-size: 16px; }
.risk-card .row { display: grid; grid-template-columns: 80px 1fr; gap: 8px; font-size: 14px; color: var(--ink-2); margin: 4px 0; }
.risk-card .row .lbl { color: var(--ink-3); font-weight: 500; }
.action-list { padding-left: 0; list-style: none; }
.action-list li {
  padding: 10px 14px; background: var(--paper); border: 1px solid var(--rule);
  border-radius: 6px; margin: 6px 0; color: var(--ink); font-size: 15px;
}
.action-list li::before { content: '✓ '; color: var(--green); font-weight: 700; }
.assumptions { padding-left: 22px; color: var(--ink-2); }
.assumptions li { margin: 6px 0; font-size: 14.5px; }
.fwd-candidate {
  background: var(--paper); border: 1px solid var(--rule); border-radius: 8px;
  padding: 18px 22px; margin: 12px 0; cursor: pointer; transition: border-color 0.15s;
}
.fwd-candidate:hover { border-color: var(--rust); }
.fwd-candidate.selected { border-color: var(--rust); border-width: 2px; background: var(--paper-2); }
.fwd-candidate h4 { margin: 0 0 6px; color: var(--ink); font-size: 18px; font-weight: 600; }
.fwd-candidate .meta { color: var(--rust); font-size: 13px; margin-bottom: 8px; }
.fwd-candidate .desc { color: var(--ink-2); font-size: 14.5px; line-height: 1.6; }
.fwd-candidate .bull-bear { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; font-size: 13px; }
.fwd-candidate .bull-bear .b { padding: 8px 12px; border-radius: 6px; }
.fwd-candidate .bull-bear .bull { background: rgba(47,125,79,0.08); color: var(--green); }
.fwd-candidate .bull-bear .bear { background: rgba(181,64,64,0.08); color: #b54040; }
@media (max-width: 720px) {
  .provider-grid, .fair-row, .method-row, .strategy-card, .scenario-row { grid-template-columns: 1fr; }
  main { padding: 14px 20px 80px; }
  h1 { font-size: 38px; }
}
"""


# ───────────────────────── Frontend JS ─────────────────────────

APP_JS = r"""
(function(){
  const KEY = 'crushValuation.sessions.v1';
  const CFG = 'crushValuation.providerConfig.v1';

  // ---------- session store ----------
  function loadStore(){
    try { return JSON.parse(localStorage.getItem(KEY)) || {sessions:{}, activeId:null}; }
    catch(e){ return {sessions:{}, activeId:null}; }
  }
  function saveStore(s){ try{ localStorage.setItem(KEY, JSON.stringify(s)); }catch(e){} }
  function getActive(){
    const st = loadStore();
    if (!st.activeId) return null;
    return st.sessions[st.activeId] || null;
  }
  function saveActive(sess){
    const st = loadStore();
    if (!sess.id) sess.id = 's_' + Date.now() + '_' + Math.random().toString(36).slice(2,8);
    sess.updated_at = Date.now();
    st.sessions[sess.id] = sess;
    st.activeId = sess.id;
    // cap 20: drop oldest by updated_at
    const ids = Object.keys(st.sessions);
    if (ids.length > 20) {
      ids.sort((a,b) => (st.sessions[a].updated_at||0) - (st.sessions[b].updated_at||0));
      while (Object.keys(st.sessions).length > 20) {
        const oldest = ids.shift();
        if (oldest === st.activeId) continue;
        delete st.sessions[oldest];
      }
    }
    saveStore(st);
    return sess.id;
  }
  function newSession(){
    return { id:'', stage:'A', description:'', dyn_schema:null, answers:{},
             forward:null, forward_choice:null, report:null, updated_at:Date.now() };
  }
  function deleteSession(id){
    const st = loadStore();
    delete st.sessions[id];
    if (st.activeId === id) st.activeId = null;
    saveStore(st);
  }
  function setActive(id){
    const st = loadStore();
    if (st.sessions[id]) { st.activeId = id; saveStore(st); }
  }
  window.__store = { loadStore, getActive, saveActive, newSession, deleteSession, setActive };

  function showToast(msg, type){
    const div = document.createElement('div');
    div.className = 'toast ' + (type||'');
    div.textContent = msg; document.body.appendChild(div);
    setTimeout(()=>div.remove(), 3500);
  }
  window.__toast = showToast;

  // ---------- provider config (separate key, persists across sessions) ----------
  function loadCfg(){
    try { return JSON.parse(localStorage.getItem(CFG)) || {provider:'deepseek', api_key:'', model:'', custom_model:'', endpoint:''}; }
    catch(e){ return {provider:'deepseek', api_key:'', model:'', custom_model:'', endpoint:''}; }
  }
  function saveCfg(c){ try{ localStorage.setItem(CFG, JSON.stringify(c)); }catch(e){} }
  window.__cfg = { loadCfg, saveCfg };

  // ---------- DOM bindings (deferred to DOMContentLoaded) ----------
  function bindTopbar(){
    document.getElementById('btn-export')?.addEventListener('click', () => {
      const sess = window.__store.getActive(); if (!sess) { showToast('无活动会话', 'error'); return; }
      const blob = new Blob([JSON.stringify(sess, null, 2)], {type:'application/json'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url;
      a.download = 'valuation-' + (sess.id||Date.now()) + '.json'; a.click();
      URL.revokeObjectURL(url); showToast('已导出', 'success');
    });
    document.getElementById('btn-import')?.addEventListener('click', () => document.getElementById('file-import').click());
    document.getElementById('file-import')?.addEventListener('change', async (e) => {
      const f = e.target.files[0]; if (!f) return;
      try {
        const obj = JSON.parse(await f.text());
        if (!obj.id) obj.id = 's_imported_' + Date.now();
        window.__store.saveActive(obj);
        showToast('已导入', 'success'); setTimeout(()=>location.href='/', 700);
      } catch(err){ showToast('导入失败: '+err.message, 'error'); }
    });
    document.getElementById('btn-home')?.addEventListener('click', () => location.href='/');
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindTopbar);
  } else {
    bindTopbar();
  }
})();
"""


HEAD = """<!doctype html><html lang="zh"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,300;9..144,500;9..144,700&family=JetBrains+Mono:wght@400;600&family=Noto+Serif+SC:wght@400;500;700&family=Noto+Sans+SC:wght@400;500;700&display=swap"/>
<link rel="stylesheet" href="/static/style.css"/>
<script src="/static/app.js"></script>
</head><body>"""

FOOTER = """<footer>对象/暧昧估值工作台 · v0.3 · 投行级估值引擎 · 多 LLM provider · 本机运行 · 12+ 文献引用</footer>
</body></html>"""


def _topbar(stage: str = "A") -> str:
    stages = ["A", "B1", "B2", "B3", "B4", "B5", "B6", "F", "D"]
    label = {"A":"描述", "B1":"她是谁", "B2":"趋势", "B3":"含金量",
             "B4":"对照", "B5":"成本", "B6":"压力", "F":"前瞻", "D":"报告"}
    pills = []
    cur_idx = stages.index(stage) if stage in stages else 0
    for i, s in enumerate(stages):
        cls = "stage-pill"
        if s == stage: cls += " active"
        elif i < cur_idx: cls += " done"
        pills.append(f'<span class="{cls}">{s}·{label[s]}</span>')
    return f"""<header class="topbar">
<div class="brand"><span class="dot">$</span>对象/暧昧 <em>估值工作台</em></div>
<div class="stages">{''.join(pills)}</div>
<div class="ctls">
<button class="ctl" id="btn-home" title="返回首页">⌂ 首页</button>
<button class="ctl" id="btn-export" title="导出">↓ 导出</button>
<button class="ctl" id="btn-import" title="导入">↑ 导入</button>
<input id="file-import" type="file" accept="application/json" style="display:none"/>
</div>
</header>"""


def _page(title: str, body: str, stage: str = "A") -> str:
    return HEAD.format(title=title) + _topbar(stage) + body + FOOTER


def _esc(s) -> str:
    return _html.escape(str(s), quote=True)


# ───────────────────────── Stage A: home + history + free-text + provider picker ─────────────────────────

def _provider_picker_html() -> str:
    return f"""<div class="card">
<h3>第 1 步 · 配置 LLM</h3>
<p style="color:var(--ink-3); font-size:14.5px; margin:0 0 14px">支持 OpenAI / DeepSeek / Claude / Gemini / 自定义 OpenAI 兼容厂商。API Key 仅存在你浏览器的 localStorage。</p>
<div class="provider-grid">
  <div class="field">
    <label class="fl">厂商</label>
    <div class="cdrop" id="prov-drop">
      <button type="button" class="cdrop-trigger"><span class="cdrop-label">DeepSeek</span><span class="arrow">▾</span></button>
      <ul class="cdrop-menu"></ul>
    </div>
  </div>
  <div class="field">
    <label class="fl">模型</label>
    <div class="cdrop" id="model-drop">
      <button type="button" class="cdrop-trigger"><span class="cdrop-label">deepseek-chat</span><span class="arrow">▾</span></button>
      <ul class="cdrop-menu"></ul>
    </div>
    <input type="text" id="model-custom" placeholder="输入自定义模型名" style="display:none; margin-top:10px"/>
  </div>
  <div class="field" style="grid-column: span 2">
    <label class="fl">API Key</label>
    <input type="password" id="api-key" placeholder="sk-..." autocomplete="off"/>
  </div>
  <div class="field" id="endpoint-wrap" style="grid-column: span 2; display:none">
    <label class="fl">自定义 endpoint (OpenAI 兼容)</label>
    <input type="text" id="endpoint-custom" placeholder="https://your-host/v1/chat/completions"/>
  </div>
</div>
<div style="display:flex; gap:14px; align-items:center; margin-top:14px; flex-wrap:wrap">
  <button type="button" class="btn-ghost" id="btn-test">测试连接</button>
  <span id="test-result"></span>
</div>
</div>

<script>
(function(){{
  const PROVIDERS = {json.dumps({k: {"name": v["name"], "models": v["models"], "default": v["default_model"], "ph": v["key_placeholder"]} for k, v in PROVIDERS.items()}, ensure_ascii=False)};

  function setupCdrop(rootId, items, currentValue, onSelect){{
    const root = document.getElementById(rootId);
    if (!root) return null;
    const trigger = root.querySelector('.cdrop-trigger');
    const labelEl = root.querySelector('.cdrop-label');
    const menu = root.querySelector('.cdrop-menu');
    let value = currentValue;
    function render(){{
      menu.innerHTML = '';
      items.forEach(it => {{
        if (it.divider) {{ const li = document.createElement('li'); li.className='divider'; menu.appendChild(li); return; }}
        const li = document.createElement('li');
        if (it.custom) li.className = 'custom-opt';
        if (String(it.value) === String(value)) li.classList.add('on');
        li.textContent = it.label;
        li.addEventListener('click', (e) => {{
          e.stopPropagation();
          value = it.value;
          const matched = items.find(x => String(x.value) === String(it.value));
          labelEl.textContent = matched ? matched.label : it.label;
          root.classList.remove('open');
          render();
          if (onSelect) onSelect(it.value);
        }});
        menu.appendChild(li);
      }});
    }}
    function setValue(v){{
      value = v;
      const it = items.find(x => String(x.value) === String(v));
      labelEl.textContent = it ? it.label : (v || '—');
      render();
    }}
    trigger.addEventListener('click', (e) => {{
      e.stopPropagation();
      document.querySelectorAll('.cdrop.open').forEach(d => {{ if (d !== root) d.classList.remove('open'); }});
      root.classList.toggle('open');
    }});
    setValue(currentValue);
    return {{ getValue: () => value, setValue }};
  }}
  document.addEventListener('click', () => {{
    document.querySelectorAll('.cdrop.open').forEach(d => d.classList.remove('open'));
  }});
  document.addEventListener('keydown', (e) => {{
    if (e.key === 'Escape') document.querySelectorAll('.cdrop.open').forEach(d => d.classList.remove('open'));
  }});

  const keyIn = document.getElementById('api-key');
  const epWrap = document.getElementById('endpoint-wrap');
  const epIn = document.getElementById('endpoint-custom');
  const modelCustom = document.getElementById('model-custom');
  const testBtn = document.getElementById('btn-test');
  const testResult = document.getElementById('test-result');

  const cfg = window.__cfg.loadCfg();
  let modelDD = null;

  function rebuildModelDD(provKey){{
    const p = PROVIDERS[provKey];
    const items = (p.models||[]).map(m => ({{ value: m, label: m }}));
    if (items.length) items.push({{ divider: true }});
    items.push({{ value: '__custom__', label: '⊕ 输入自定义模型名…', custom: true }});
    let initial = cfg.model;
    if (provKey !== cfg.provider) initial = '';
    if (!initial && cfg.custom_model && provKey === cfg.provider) initial = '__custom__';
    if (!initial || !items.some(it => String(it.value) === String(initial))) {{
      initial = (p.models && p.models[0]) || '__custom__';
    }}
    modelDD = setupCdrop('model-drop', items, initial, (val) => {{
      modelCustom.style.display = (val === '__custom__') ? '' : 'none';
      snap();
    }});
    modelCustom.style.display = (initial === '__custom__') ? '' : 'none';
  }}

  const provItems = Object.keys(PROVIDERS).map(k => ({{ value: k, label: PROVIDERS[k].name }}));
  const provInitial = cfg.provider in PROVIDERS ? cfg.provider : 'deepseek';
  const provDD = setupCdrop('prov-drop', provItems, provInitial, (val) => {{
    rebuildModelDD(val);
    keyIn.placeholder = (PROVIDERS[val].ph) || 'API Key';
    epWrap.style.display = (val === 'custom') ? '' : 'none';
    snap();
  }});
  rebuildModelDD(provInitial);
  keyIn.placeholder = (PROVIDERS[provInitial].ph) || 'API Key';
  epWrap.style.display = (provInitial === 'custom') ? '' : 'none';
  keyIn.value = cfg.api_key || '';
  epIn.value = cfg.endpoint || '';
  if (cfg.custom_model) modelCustom.value = cfg.custom_model;

  function snap(){{
    const provider = provDD.getValue();
    const modelSel = modelDD ? modelDD.getValue() : '';
    window.__cfg.saveCfg({{
      provider,
      api_key: keyIn.value.trim(),
      model: modelSel === '__custom__' ? '' : modelSel,
      custom_model: modelSel === '__custom__' ? modelCustom.value.trim() : '',
      endpoint: epIn.value.trim(),
    }});
  }}
  [keyIn, modelCustom, epIn].forEach(el => el.addEventListener('input', snap));

  testBtn.addEventListener('click', async () => {{
    snap();
    testResult.innerHTML = '<span class="spinner" style="border-color:rgba(0,0,0,0.15); border-top-color:var(--rust)"></span> <span style="margin-left:6px; color:var(--ink-3)">测试中…</span>';
    try {{
      const c = window.__cfg.loadCfg();
      const r = await fetch('/api/probe_connection', {{
        method:'POST', headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{
          provider: c.provider, api_key: c.api_key,
          model: c.model || c.custom_model, endpoint: c.endpoint,
        }}),
      }});
      const data = await r.json();
      if (data.ok) testResult.innerHTML = '<span class="test-result ok">✓ 连接成功: ' + (data.content||'').slice(0,40) + '</span>';
      else testResult.innerHTML = '<span class="test-result fail">✗ ' + (data.error||'未知').slice(0,140) + '</span>';
    }} catch(e) {{
      testResult.innerHTML = '<span class="test-result fail">✗ ' + e.message + '</span>';
    }}
  }});
}})();
</script>"""


def _history_list_html() -> str:
    return """<div class="card subtle">
<h3 style="margin:0 0 8px">历史会话</h3>
<p style="margin:0; font-size:14px; color:var(--ink-3)">点击继续会自动恢复你之前的所有进度（最多保留 20 条）</p>
<div class="history-list" id="history-list">
  <div style="color:var(--ink-3); padding:14px; text-align:center; font-size:14px">加载中…</div>
</div>
</div>
<script>
(function(){
  const list = document.getElementById('history-list');
  const st = window.__store.loadStore();
  const ids = Object.keys(st.sessions);
  if (!ids.length) { list.innerHTML = '<div style="color:var(--ink-3); padding:14px; text-align:center; font-size:14px">还没有历史会话 — 在下方开始你的第一次估值</div>'; return; }
  ids.sort((a,b) => (st.sessions[b].updated_at||0) - (st.sessions[a].updated_at||0));
  list.innerHTML = ids.map(id => {
    const s = st.sessions[id];
    const desc = (s.description||'(无描述)').slice(0, 60);
    const stage = s.stage || 'A';
    const ago = timeAgo(s.updated_at);
    return `<div class="history-item">
      <div class="desc">${escapeHtml(desc)}</div>
      <div class="meta">${stage} · ${ago}</div>
      <div class="actions">
        <button class="btn-ghost" data-act="continue" data-id="${id}">继续</button>
        <button class="btn-ghost" data-act="delete" data-id="${id}" style="color:#b54040; border-color:#b54040">删除</button>
      </div>
    </div>`;
  }).join('');
  list.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-act]'); if (!btn) return;
    const id = btn.dataset.id, act = btn.dataset.act;
    if (act === 'continue') {
      window.__store.setActive(id);
      const s = st.sessions[id];
      const stage = s.stage || 'A';
      const path = stage === 'A' ? '/' : (stage === 'F' ? '/stage/f' : (stage === 'D' ? '/stage/d' : '/stage/' + stage.toLowerCase()));
      location.href = path;
    } else if (act === 'delete') {
      if (confirm('确定删除这条会话?')) { window.__store.deleteSession(id); location.reload(); }
    }
  });
  function timeAgo(ts){
    if (!ts) return '';
    const d = (Date.now()-ts)/1000;
    if (d<60) return '刚刚';
    if (d<3600) return Math.floor(d/60)+' 分钟前';
    if (d<86400) return Math.floor(d/3600)+' 小时前';
    return Math.floor(d/86400)+' 天前';
  }
  function escapeHtml(s){ return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
})();
</script>"""


def _stage_a_body() -> str:
    return f"""<main>
<p class="eyebrow">投行级估值 · 多 LLM provider · 100% 本机运行</p>
<h1>给你的<em>对象</em>或<em>暧昧对象</em><br/>做投行级估值</h1>
<p class="lede">第一步: 用一段话描述 TA + 你们的关系现状。LLM 会根据你的描述, 个性化生成 6 阶段问卷 (对标 IPO 估值流程: 业务理解 → 历史 → 预测 → DCF → 可比 → 压力测试)。然后引擎会跑完整的三法估值, 再请 LLM 写一份投行级别的估值备忘录。</p>

{_history_list_html()}

{_provider_picker_html()}

<form id="stage-a-form">
<div class="card">
<h3>第 2 步 · 描述对象 / 暧昧对象</h3>
<div class="field" style="margin:0">
<label class="fl">描述 TA + 你们的关系</label>
<textarea id="description" class="bigdesc" placeholder="例: 我们暧昧 3 个月了, TA 在金融行业, 工作很忙, 但每周末会主动约我吃饭。最近开始介绍我给 TA 的朋友。TA 上一段感情结束才半年, 我有点担心 TA 还没走出来..."></textarea>
<div class="hint">越具体越好。LLM 会根据你提到的细节 (异地? 工作忙? 前任阴影? 年龄差?) 动态生成对应的问题。</div>
</div>
<div style="margin-top:14px; display:flex; gap:14px; align-items:center">
<button class="btn" id="btn-submit-a" type="submit">生成 6 阶段问卷 →</button>
<label style="font-size:14px; color:var(--ink-3); display:flex; align-items:center; gap:6px">
  <input type="checkbox" id="use-fallback"/> 跳过 LLM, 用通用模板
</label>
</div>
</div>
</form>

<p class="privacy-banner">所有数据仅存在你浏览器的 localStorage · API Key 永不上传服务端日志 · 完全本机运行</p>
</main>

<script>
(function(){{
  const form = document.getElementById('stage-a-form');
  form.addEventListener('submit', async (e) => {{
    e.preventDefault();
    const desc = document.getElementById('description').value.trim();
    if (!desc) {{ window.__toast('请先描述一下', 'error'); return; }}
    const useFallback = document.getElementById('use-fallback').checked;
    const cfg = window.__cfg.loadCfg();
    const btn = document.getElementById('btn-submit-a');
    btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> 生成中, 大约 20-40 秒…';

    try {{
      const body = useFallback
        ? {{ fallback: true, description: desc }}
        : {{
            provider: cfg.provider, api_key: cfg.api_key,
            model: cfg.model || cfg.custom_model, endpoint: cfg.endpoint,
            description: desc,
          }};
      if (!useFallback && !cfg.api_key) {{
        window.__toast('请先填 API Key 或勾选「跳过 LLM」', 'error');
        btn.disabled = false; btn.textContent = '生成 6 阶段问卷 →'; return;
      }}
      const r = await fetch('/api/generate', {{ method:'POST', headers:{{'Content-Type':'application/json'}}, body: JSON.stringify(body) }});
      const data = await r.json();
      if (!data.ok) throw new Error(data.error || '未知错误');
      const sess = window.__store.newSession();
      sess.description = desc;
      sess.dyn_schema = data.schema;
      sess.stage = 'B1';
      window.__store.saveActive(sess);
      location.href = '/stage/b1';
    }} catch(err) {{
      window.__toast('生成失败: ' + err.message + ' (可勾选「跳过 LLM」继续)', 'error');
      btn.disabled = false; btn.textContent = '生成 6 阶段问卷 →';
    }}
  }});
}})();
</script>"""


# ───────────────────────── Stage B1-B6: render one stage's subthemes + fields ─────────────────────────

def _render_field(f) -> str:
    label = _esc(f["label_zh"])
    fid = _esc(f["id"])
    hint = f'<div class="hint">{_esc(f["hint_zh"])}</div>' if f.get("hint_zh") else ""
    anchors = ""
    if f.get("anchor_low_zh") or f.get("anchor_high_zh"):
        anchors = f"""<div class="anchors">
<span class="lo">↓ {_esc(f.get('anchor_low_zh',''))}</span>
<span class="hi">{_esc(f.get('anchor_high_zh',''))} ↑</span>
</div>"""
    kind = f["kind"]
    if kind in ("likert5", "likert7"):
        n = 5 if kind == "likert5" else 7
        opts = "".join(f'<span class="likert-opt" data-val="{i}">{i}</span>' for i in range(1, n+1))
        return f"""<div class="field">
<label class="fl">{label}</label>
{anchors}
<div class="likert-row" data-likert="{fid}">{opts}</div>
{hint}
</div>"""
    if kind == "range":
        default = _esc(f.get("default", (f["min"]+f["max"])/2))
        return f"""<div class="field">
<label class="fl">{label} <span class="vdisp" id="{fid}-disp">{default}</span></label>
{anchors}
<input type="range" name="{fid}" min="{f['min']}" max="{f['max']}" step="{f['step']}" value="{default}"/>
{hint}
</div>"""
    if kind == "number":
        default = _esc(f.get("default", 0))
        return f"""<div class="field">
<label class="fl">{label}</label>
<input type="number" name="{fid}" min="{f['min']}" max="{f['max']}" step="{f['step']}" value="{default}"/>
{hint}
</div>"""
    if kind == "select":
        opts = f.get("options") or []
        opts_html = "".join(f'<option value="{_esc(o[0])}">{_esc(o[1])}</option>' for o in opts)
        return f"""<div class="field">
<label class="fl">{label}</label>
<select name="{fid}">{opts_html}</select>
{hint}
</div>"""
    # fillin
    return f"""<div class="field">
<label class="fl">{label}</label>
<input type="text" name="{fid}" value=""/>
{hint}
</div>"""


def _stage_b_body(stage_id: str, next_stage: str) -> str:
    """Stage B1-B6: client-side renders the schema for the given stage from localStorage."""
    return f"""<main>
<div id="b-content"><div class="card"><p>加载中…</p></div></div>
</main>
<script>
(function(){{
  const sess = window.__store.getActive();
  if (!sess || !sess.dyn_schema) {{ document.getElementById('b-content').innerHTML = '<div class="card"><h2>无活动会话</h2><p>请先<a href="/">从首页开始</a>。</p></div>'; return; }}
  const schema = sess.dyn_schema;
  const stages = schema.stages || [];
  const stage = stages.find(s => s.id === '{stage_id}');
  if (!stage) {{ document.getElementById('b-content').innerHTML = '<div class="card"><h2>未找到该阶段</h2><p><a href="/">返回首页</a></p></div>'; return; }}

  const stageIdx = stages.findIndex(s => s.id === '{stage_id}') + 1;
  const totalStages = stages.length;

  function renderField(f) {{
    return {json.dumps(None)};  // placeholder, replaced below
  }}
  const FIELD_RENDERERS = {{}};

  function fieldHtml(f) {{
    const label = escapeHtml(f.label_zh || f.id);
    const fid = escapeHtml(f.id);
    const hint = f.hint_zh ? '<div class="hint">' + escapeHtml(f.hint_zh) + '</div>' : '';
    let anchors = '';
    if (f.anchor_low_zh || f.anchor_high_zh) {{
      anchors = '<div class="anchors"><span class="lo">↓ ' + escapeHtml(f.anchor_low_zh||'') + '</span><span class="hi">' + escapeHtml(f.anchor_high_zh||'') + ' ↑</span></div>';
    }}
    const kind = f.kind;
    if (kind === 'likert5' || kind === 'likert7') {{
      const n = kind === 'likert5' ? 5 : 7;
      let opts = '';
      for (let i=1; i<=n; i++) opts += '<span class="likert-opt" data-val="'+i+'">'+i+'</span>';
      return '<div class="field"><label class="fl">'+label+'</label>'+anchors+'<div class="likert-row" data-likert="'+fid+'">'+opts+'</div>'+hint+'</div>';
    }}
    if (kind === 'range') {{
      const def = f.default ?? ((f.min+f.max)/2);
      return '<div class="field"><label class="fl">'+label+' <span class="vdisp" id="'+fid+'-disp">'+def+'</span></label>'+anchors+'<input type="range" name="'+fid+'" min="'+f.min+'" max="'+f.max+'" step="'+f.step+'" value="'+def+'"/>'+hint+'</div>';
    }}
    if (kind === 'number') {{
      const def = f.default ?? 0;
      return '<div class="field"><label class="fl">'+label+'</label><input type="number" name="'+fid+'" min="'+f.min+'" max="'+f.max+'" step="'+f.step+'" value="'+def+'"/>'+hint+'</div>';
    }}
    if (kind === 'select') {{
      const opts = (f.options||[]).map(o => {{
        const v = Array.isArray(o) ? o[0] : o.value;
        const l = Array.isArray(o) ? o[1] : (o.label_zh || o.label || o.value);
        return '<option value="'+escapeHtml(v)+'">'+escapeHtml(l)+'</option>';
      }}).join('');
      return '<div class="field"><label class="fl">'+label+'</label><select name="'+fid+'">'+opts+'</select>'+hint+'</div>';
    }}
    return '<div class="field"><label class="fl">'+label+'</label><input type="text" name="'+fid+'" value=""/>'+hint+'</div>';
  }}
  function escapeHtml(s){{ return String(s||'').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); }}

  let html = '<p class="eyebrow">阶段 ' + stage.id + ' · ' + stageIdx + ' / ' + totalStages + '</p>';
  html += '<h1>' + escapeHtml(stage.label_zh) + '</h1>';
  html += '<div class="stage-why"><span class="lbl">为什么这一步</span><p>' + escapeHtml(stage.why_matters_zh||'') + '</p></div>';
  html += '<form id="stage-form">';
  (stage.sub_themes||[]).forEach(sub => {{
    html += '<div class="subtheme-card"><h3>' + escapeHtml(sub.name_zh) + '</h3>';
    if (sub.why_zh) html += '<p>' + escapeHtml(sub.why_zh) + '</p>';
    html += '</div>';
    (sub.fields||[]).forEach(f => {{ html += fieldHtml(f); }});
  }});
  html += '<div style="display:flex; gap:14px; align-items:center; margin-top:20px">';
  if (stage.id !== 'B1') html += '<button type="button" class="btn-ghost" id="btn-prev">← 上一步</button>';
  html += '<button class="btn" type="submit">下一步 →</button>';
  html += '</div></form>';
  document.getElementById('b-content').innerHTML = html;

  // wire likert + auto-save
  const form = document.getElementById('stage-form');
  function readAnswers() {{
    const out = Object.assign({{}}, sess.answers || {{}});
    Array.from(form.elements).forEach(el => {{
      if (!el.name) return;
      if (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA') {{
        out[el.name] = el.value;
      }}
    }});
    form.querySelectorAll('[data-likert]').forEach(g => {{
      const fid = g.getAttribute('data-likert');
      const sel = g.querySelector('.likert-opt.on');
      if (sel) out[fid] = sel.getAttribute('data-val');
    }});
    return out;
  }}
  function snap() {{
    sess.answers = readAnswers();
    sess.stage = '{stage_id}';
    window.__store.saveActive(sess);
    form.querySelectorAll('input[type=range]').forEach(r => {{
      const d = document.getElementById(r.name + '-disp'); if (d) d.textContent = r.value;
    }});
  }}
  Array.from(form.elements).forEach(el => {{
    el.addEventListener('input', snap); el.addEventListener('change', snap);
  }});
  form.querySelectorAll('.likert-opt').forEach(opt => {{
    opt.addEventListener('click', (e) => {{
      e.preventDefault();
      const group = opt.parentElement;
      group.querySelectorAll('.likert-opt').forEach(x => x.classList.remove('on'));
      opt.classList.add('on'); snap();
    }});
  }});
  // restore prior answers
  const ans = sess.answers || {{}};
  Object.keys(ans).forEach(fid => {{
    const v = ans[fid];
    const el = form.elements[fid];
    if (el) {{ el.value = v; }}
    const lk = form.querySelector('[data-likert="'+CSS.escape(fid)+'"]');
    if (lk) {{
      lk.querySelectorAll('.likert-opt').forEach(opt => {{
        if (opt.getAttribute('data-val') === String(v)) opt.classList.add('on');
      }});
    }}
  }});
  form.querySelectorAll('input[type=range]').forEach(r => {{
    const d = document.getElementById(r.name + '-disp'); if (d) d.textContent = r.value;
  }});

  document.getElementById('btn-prev')?.addEventListener('click', () => {{
    const order = ['B1','B2','B3','B4','B5','B6'];
    const idx = order.indexOf('{stage_id}');
    if (idx > 0) {{ sess.stage = order[idx-1]; window.__store.saveActive(sess); location.href = '/stage/' + order[idx-1].toLowerCase(); }}
  }});
  form.addEventListener('submit', (e) => {{
    e.preventDefault(); snap();
    sess.stage = '{next_stage}'; window.__store.saveActive(sess);
    location.href = '{("/stage/f" if next_stage == "F" else "/stage/" + next_stage.lower())}';
  }});
}})();
</script>"""


# ───────────────────────── Stage F: forward variables (LLM-driven) ─────────────────────────

def _stage_f_body() -> str:
    return f"""<main>
<div id="f-content"><div class="card"><p><span class="spinner" style="border-color:rgba(0,0,0,0.2); border-top-color:var(--rust)"></span> 正在让 LLM 分析你的答案, 提炼 2-3 个最关键的前瞻变量…</p></div></div>
</main>
<script>
(function(){{
  const sess = window.__store.getActive();
  if (!sess || !sess.dyn_schema) {{ document.getElementById('f-content').innerHTML = '<div class="card"><h2>无活动会话</h2><p><a href="/">返回首页</a></p></div>'; return; }}

  function escapeHtml(s){{ return String(s||'').replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); }}

  function render(forward) {{
    sess.forward = forward;
    // Auto-select recommended (or first) candidate if none chosen yet
    if (!sess.forward_choice && forward.candidates && forward.candidates.length) {{
      const rec = forward.candidates.find(c => c.recommended) || forward.candidates[0];
      if (rec) sess.forward_choice = rec;
    }}
    window.__store.saveActive(sess);
    let html = '<p class="eyebrow">阶段 F · 前瞻变量与三场景</p>';
    html += '<h1>挑一个 <em>前瞻变量</em></h1>';
    html += '<div class="stage-why"><span class="lbl">什么是前瞻变量</span><p>' + escapeHtml(forward.explanation_zh || '') + '</p></div>';
    html += '<p class="lede">下面是 LLM 根据你前面的全部答案 + 描述, 提炼出来的最相关 ' + (forward.candidates||[]).length + ' 个候选。选一个最贴合你情况的:</p>';
    (forward.candidates||[]).forEach((c, i) => {{
      const sel = (sess.forward_choice && sess.forward_choice.id === c.id) || (!sess.forward_choice && c.recommended) ? 'selected' : '';
      const recBadge = c.recommended ? '<span style="background:rgba(196,99,42,0.12); color:var(--rust); padding:2px 8px; border-radius:4px; font-size:12px; margin-left:8px">推荐</span>' : '';
      html += '<div class="fwd-candidate ' + sel + '" data-id="' + escapeHtml(c.id) + '">';
      html += '<h4>' + escapeHtml(c.name_zh) + recBadge + '</h4>';
      html += '<div class="meta">扰动幅度 Δ = ' + Math.round((c.delta_pct||0.3)*100) + '%  ·  ' + escapeHtml(c.delta_pct_rationale_zh||'') + '</div>';
      html += '<div class="desc">' + escapeHtml(c.rationale_zh||'') + '</div>';
      html += '<div class="bull-bear"><div class="b bull">↑ Bull: ' + escapeHtml(c.bull_meaning_zh||'') + '</div><div class="b bear">↓ Bear: ' + escapeHtml(c.bear_meaning_zh||'') + '</div></div>';
      html += '</div>';
    }});
    html += '<div style="display:flex; gap:14px; margin-top:20px">';
    html += '<button type="button" class="btn-ghost" id="btn-prev">← 上一步</button>';
    html += '<button type="button" class="btn" id="btn-next">下一步 · 生成估值报告 →</button>';
    html += '</div>';
    document.getElementById('f-content').innerHTML = html;

    document.querySelectorAll('.fwd-candidate').forEach(card => {{
      card.addEventListener('click', () => {{
        document.querySelectorAll('.fwd-candidate').forEach(x => x.classList.remove('selected'));
        card.classList.add('selected');
        const id = card.dataset.id;
        const c = (forward.candidates||[]).find(x => x.id === id);
        if (c) {{ sess.forward_choice = c; window.__store.saveActive(sess); }}
      }});
    }});
    document.getElementById('btn-prev').addEventListener('click', () => {{
      sess.stage = 'B6'; window.__store.saveActive(sess); location.href = '/stage/b6';
    }});
    document.getElementById('btn-next').addEventListener('click', async () => {{
      if (!sess.forward_choice) {{ window.__toast('请选一个候选前瞻变量', 'error'); return; }}
      const btn = document.getElementById('btn-next');
      btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> 计算估值并生成叙事中…';
      try {{
        const cfg = window.__cfg.loadCfg();
        const r = await fetch('/api/compute_full', {{
          method:'POST', headers:{{'Content-Type':'application/json'}},
          body: JSON.stringify({{
            description: sess.description,
            dyn_schema: sess.dyn_schema,
            answers: sess.answers || {{}},
            forward_choice: sess.forward_choice,
            llm: {{
              provider: cfg.provider, api_key: cfg.api_key,
              model: cfg.model || cfg.custom_model, endpoint: cfg.endpoint,
            }},
          }}),
        }});
        const data = await r.json();
        if (!data.id) throw new Error(data.error || '未知');
        sess.report_id = data.id;
        sess.report = data.report;
        sess.narrative = data.narrative;
        sess.stage = 'D'; window.__store.saveActive(sess);
        location.href = '/stage/d?id=' + encodeURIComponent(data.id);
      }} catch(err) {{
        window.__toast('计算失败: ' + err.message, 'error');
        btn.disabled = false; btn.textContent = '下一步 · 生成估值报告 →';
      }}
    }});
  }}

  // If we already have forward in session, render directly
  if (sess.forward) {{ render(sess.forward); return; }}

  // Else call LLM
  (async () => {{
    const cfg = window.__cfg.loadCfg();
    try {{
      const r = await fetch('/api/forward', {{
        method:'POST', headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{
          description: sess.description,
          dyn_schema: sess.dyn_schema,
          answers: sess.answers || {{}},
          llm: {{
            provider: cfg.provider, api_key: cfg.api_key,
            model: cfg.model || cfg.custom_model, endpoint: cfg.endpoint,
          }},
        }}),
      }});
      const data = await r.json();
      if (!data.ok) throw new Error(data.error || '未知');
      render(data.forward);
    }} catch(err) {{
      window.__toast('前瞻分析失败, 使用通用模板: ' + err.message, 'error');
      render({json.dumps(FALLBACK_FORWARD, ensure_ascii=False)});
    }}
  }})();
}})();
</script>"""


# ───────────────────────── Stage D: full IB-grade report ─────────────────────────

def _render_report_html(report, narrative: dict, rid: str) -> str:
    tear_svg = render_tear_sheet(report)
    sens_svg = render_sensitivity_heatmap(report)
    scen_svg = render_scenario_comparison(report)
    bl = report.blended
    mc = report.mc

    fair_html = ""
    method_html = ""
    if bl is not None:
        fair_html = f"""<div class="fair-row">
<div class="fair-cell"><div class="lbl">悲观 P10</div><div class="val">{bl.fair_low:.2f}</div></div>
<div class="fair-cell mid"><div class="lbl">中性 P50 (公允价值)</div><div class="val">{bl.fair_mid:.2f}</div></div>
<div class="fair-cell"><div class="lbl">乐观 P90</div><div class="val">{bl.fair_high:.2f}</div></div>
</div>"""
        method_html = f"""<div class="method-row">
<div class="method-cell"><div class="lbl">DCF 三阶段法 (内在价值)</div><div class="val">{bl.dcf_value:.2f}</div><div class="w">权重 {bl.weights[0]*100:.0f}%</div></div>
<div class="method-cell"><div class="lbl">可比公司倍数</div><div class="val">{bl.multiples_value:.2f}</div><div class="w">权重 {bl.weights[1]*100:.0f}%</div></div>
<div class="method-cell"><div class="lbl">资产 / 重置法</div><div class="val">{bl.asset_value:.2f}</div><div class="w">权重 {bl.weights[2]*100:.0f}%</div></div>
</div>"""

    mc_html = ""
    if mc is not None:
        mc_html = f"""<p class="lede">蒙特卡洛 ({mc.iters} 次抽样) · P10 = <strong>{mc.p10:.2f}</strong> · P50 = <strong>{mc.p50:.2f}</strong> · P90 = <strong>{mc.p90:.2f}</strong> · 公允&gt;成本概率 = <strong>{mc.prob_above_cost*100:.1f}%</strong></p>"""

    # Narrative blocks
    n = narrative or {}
    thesis = _esc(n.get("thesis_zh", "")).replace("\n\n", "</p><p>").replace("\n", "<br/>")
    verdict = _esc(n.get("verdict_one_liner_zh", ""))

    bull_n = _esc(n.get("bull_narrative_zh", ""))
    base_n = _esc(n.get("base_narrative_zh", ""))
    bear_n = _esc(n.get("bear_narrative_zh", ""))

    risks_html = ""
    for r in (n.get("top_risks") or []):
        risks_html += f"""<div class="risk-card">
<div class="h">⚠ {_esc(r.get("title_zh", ""))}</div>
<div class="row"><div class="lbl">触发</div><div>{_esc(r.get("trigger_zh", ""))}</div></div>
<div class="row"><div class="lbl">后果</div><div>{_esc(r.get("consequence_zh", ""))}</div></div>
<div class="row"><div class="lbl">早期信号</div><div>{_esc(r.get("early_signal_zh", ""))}</div></div>
</div>"""

    def _ul(items):
        if not items:
            return ""
        return '<ul class="action-list">' + "".join(f"<li>{_esc(x)}</li>" for x in items) + "</ul>"

    actions_w = _ul(n.get("actions_this_week_zh") or [])
    actions_m = _ul(n.get("actions_this_month_zh") or [])
    actions_q = _ul(n.get("actions_quarter_zh") or [])

    assumptions_html = ""
    if n.get("key_assumptions_zh"):
        assumptions_html = '<ul class="assumptions">' + "".join(f"<li>{_esc(a)}</li>" for a in n["key_assumptions_zh"]) + "</ul>"

    # Strategy / archetype
    arch_label = report.archetype.label_zh
    arch_desc = report.archetype.description_zh

    scenario_pills = ""
    for name, sc in report.scenarios.items():
        if isinstance(sc, dict):
            zh_name = {"bear":"悲观 BEAR","base":"中性 BASE","bull":"乐观 BULL"}.get(name, name)
            scenario_pills += f"""<div class="scenario-pill">
<div class="name">{zh_name}</div>
<div class="vals">每期价值 EPS: {sc.get('E',0):.2f}<br/>成长率 g: {sc.get('g',0)*100:+.1f}%<br/>折现率: {sc.get('wacc',0)*100:.1f}%<br/>公允价值: {sc.get('fair_mid',0):.2f}<br/>上行: {sc.get('upside_pct',0)*100:+.0f}%</div>
</div>"""

    warn_html = ""
    if report.warnings:
        warn_html = '<div class="warnings">⚠ ' + " · ".join(_esc(w) for w in report.warnings) + '</div>'

    cite_html = "".join(f"<li>{_esc(c)}</li>" for c in report.citations)

    return f"""<main>
<p class="eyebrow">阶段 D · 估值备忘录 · {rid}</p>
<h1>{_esc(verdict or "估值报告")}</h1>

<div class="tear-wrap">{tear_svg}</div>

{warn_html}

<h2 class="section-label"><span class="num">01</span> 综合公允价值带</h2>
{fair_html}
{method_html}
<p class="lede">投入成本 (你已付的时间+情绪+钱) <strong>{report.ib_inputs.investment_cost:.2f}</strong> · 综合 P50 上行空间 <strong>{(bl.upside_pct*100 if bl else 0):+.1f}%</strong> · P/E 倍数 <strong>{(bl.pe_final if bl else 0):.2f}</strong> · P/B 倍数 <strong>{(bl.pb_final if bl else 0):.2f}</strong> · 每期价值 EPS <strong>{(bl.eps if bl else 0):.2f}</strong></p>
{mc_html}

<h2 class="section-label"><span class="num">02</span> 投资论点 (Thesis)</h2>
<div class="thesis-block"><p>{thesis}</p></div>

<h2 class="section-label"><span class="num">03</span> 三场景叙事</h2>
<div class="scenario-narrative"><div class="h">↑ 乐观 (Bull)</div><p>{bull_n}</p></div>
<div class="scenario-narrative"><div class="h">→ 中性 (Base)</div><p>{base_n}</p></div>
<div class="scenario-narrative"><div class="h">↓ 悲观 (Bear)</div><p>{bear_n}</p></div>
<div class="scenario-row">{scenario_pills}</div>
<div class="svg-card">{scen_svg}</div>

<h2 class="section-label"><span class="num">04</span> 自动分类 (Archetype) + 仓位建议</h2>
<div class="archetype-card">
<div class="arch-fit">类型 · 拟合度 {report.archetype.fit_score*100:.0f}%</div>
<p class="arch-label">{_esc(arch_label)}</p>
<p class="arch-desc">{_esc(arch_desc)}</p>
</div>
<div class="strategy-card">
<div class="strat-pill"><div class="label">仓位</div><div class="value">{_esc(report.strategy.position)}</div></div>
<div class="strat-pill"><div class="label">持有期</div><div class="value">{_esc(report.strategy.hold_period)}</div></div>
<div class="strat-pill"><div class="label">信念度</div><div class="value">{_esc(report.strategy.conviction)}</div></div>
</div>

<h2 class="section-label"><span class="num">05</span> Top 3 风险</h2>
{risks_html or "<p class='lede'>暂无风险叙事 — 检查 LLM 配置。</p>"}

<h2 class="section-label"><span class="num">06</span> 行动清单</h2>
<h3>本周</h3>{actions_w}
<h3>本月</h3>{actions_m}
<h3>未来 1-3 月</h3>{actions_q}

<h2 class="section-label"><span class="num">07</span> 退出策略</h2>
<div class="thesis-block"><p>{_esc(n.get("exit_strategy_zh", ""))}</p></div>

<h2 class="section-label"><span class="num">08</span> 横向对照叙事</h2>
<div class="thesis-block"><p>{_esc(n.get("comparable_narrative_zh", ""))}</p></div>

<h2 class="section-label"><span class="num">09</span> 关键假设</h2>
{assumptions_html}

<h2 class="section-label"><span class="num">10</span> 敏感性分析</h2>
<div class="svg-card">{sens_svg}</div>

<h2 class="section-label"><span class="num">11</span> 导出</h2>
<p>
<a class="btn-ghost" href="/export/{rid}.md">↓ Markdown</a>
<a class="btn-ghost" href="/export/{rid}.json">↓ JSON</a>
<a class="btn-ghost" href="/" style="margin-left:14px">↻ 新建估值</a>
</p>

<h2 class="section-label"><span class="num">12</span> 文献引用</h2>
<ul style="padding-left:20px; color:var(--ink-3); font-size:13.5px">{cite_html}</ul>

<p class="privacy-banner">本估值基于投行方法的隐喻映射 · 半严肃 meme 工具 · 不构成财务建议或心理咨询</p>
</main>"""


# ───────────────────────── HTTP Handler ─────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass

    def do_GET(self):
        path = self.path.split("?")[0]
        query = urllib.parse.parse_qs(self.path.split("?", 1)[1]) if "?" in self.path else {}

        if path == "/":
            self._html(_page("对象/暧昧估值工作台", _stage_a_body(), "A")); return
        if path.startswith("/stage/b"):
            stage_id = path[len("/stage/"):].upper()
            if stage_id not in ("B1","B2","B3","B4","B5","B6"):
                self._send("not found", "text/plain", 404); return
            order = ["B1","B2","B3","B4","B5","B6"]
            idx = order.index(stage_id)
            next_stage = order[idx+1] if idx + 1 < len(order) else "F"
            self._html(_page(f"阶段 {stage_id}", _stage_b_body(stage_id, next_stage), stage_id)); return
        if path == "/stage/f":
            self._html(_page("前瞻变量", _stage_f_body(), "F")); return
        if path == "/stage/d":
            rid = query.get("id", [""])[0]
            data = SESSION_CACHE.get(rid)
            if data:
                html = _render_report_html(data["report"], data.get("narrative") or {}, rid)
                self._html(_page("估值报告", html, "D")); return
            # Try render from localStorage via JS shell
            self._html(_page("估值报告", _stage_d_shell(), "D")); return
        if path == "/static/style.css":
            self._send(STYLE_CSS, "text/css; charset=utf-8"); return
        if path == "/static/app.js":
            self._send(APP_JS, "application/javascript; charset=utf-8"); return
        if path.startswith("/export/"):
            if path.endswith(".md"):
                rid = path[len("/export/"):-3]
                d = SESSION_CACHE.get(rid)
                if not d: self._send("not found","text/plain",404); return
                self._send(to_markdown(d["report"], lang="zh"), "text/markdown; charset=utf-8"); return
            if path.endswith(".json"):
                rid = path[len("/export/"):-5]
                d = SESSION_CACHE.get(rid)
                if not d: self._send("not found","text/plain",404); return
                self._send(to_json(d["report"]), "application/json; charset=utf-8"); return
        self._send("not found", "text/plain", 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            self._json({"ok": False, "error":"invalid json"}, 400); return

        if self.path == "/api/probe_connection": self._handle_test(body); return
        if self.path == "/api/generate":         self._handle_generate(body); return
        if self.path == "/api/forward":          self._handle_forward(body); return
        if self.path == "/api/compute_full":     self._handle_compute_full(body, raw); return
        self._json({"ok": False, "error": "not found"}, 404)

    def _handle_test(self, body: dict):
        provider = body.get("provider", "")
        api_key = body.get("api_key", "")
        model = body.get("model", "")
        endpoint = body.get("endpoint", "")
        result = probe_connection(provider, api_key, model, endpoint)
        self._json(result)

    def _handle_generate(self, body: dict):
        desc = (body.get("description") or "").strip()
        if body.get("fallback") or not body.get("api_key"):
            schema = get_fallback_schema()
        else:
            messages = build_schema_prompt(desc)
            try:
                text = call_llm(
                    body.get("provider", ""), body.get("api_key", ""),
                    body.get("model", ""), messages,
                    endpoint=body.get("endpoint", ""), max_tokens=8000,
                )
                obj = parse_llm_json(text)
                schema = parse_dyn_schema(obj)
            except (ProviderError, ParseError) as e:
                self._json({"ok": False, "error": str(e)}, 400); return
            except Exception as e:
                self._json({"ok": False, "error": f"未预期: {e}"}, 500); return
        sid = hashlib.sha1((desc + str(id(schema))).encode("utf-8")).hexdigest()[:12]
        SCHEMA_CACHE[sid] = schema
        self._json({"ok": True, "sid": sid, "schema": schema.to_dict()})

    def _handle_forward(self, body: dict):
        desc = body.get("description", "")
        schema_dict = body.get("dyn_schema") or {}
        answers = body.get("answers") or {}
        llm = body.get("llm") or {}
        schema = parse_dyn_schema(schema_dict) if schema_dict else get_fallback_schema()
        ib = aggregate_ib_inputs(schema, answers)
        if not llm.get("api_key"):
            self._json({"ok": True, "forward": FALLBACK_FORWARD}); return
        try:
            messages = build_forward_prompt(
                desc, schema_to_summary(schema), answers_to_summary(answers), ib_to_summary(ib),
            )
            text = call_llm(llm.get("provider",""), llm.get("api_key",""),
                            llm.get("model",""), messages,
                            endpoint=llm.get("endpoint",""), max_tokens=2400)
            obj = parse_llm_json(text)
            self._json({"ok": True, "forward": obj})
        except (ProviderError, ParseError) as e:
            self._json({"ok": True, "forward": FALLBACK_FORWARD, "warning": str(e)[:200]})
        except Exception as e:
            self._json({"ok": True, "forward": FALLBACK_FORWARD, "warning": f"未预期: {e}"[:200]})

    def _handle_compute_full(self, body: dict, raw: str):
        try:
            desc = body.get("description", "")
            schema_dict = body.get("dyn_schema") or {}
            answers = body.get("answers") or {}
            forward_choice = body.get("forward_choice") or {}
            llm = body.get("llm") or {}
            schema = parse_dyn_schema(schema_dict) if schema_dict else get_fallback_schema()
            delta_pct = float(forward_choice.get("delta_pct", 0.30))
            forward_var_name = forward_choice.get("name_zh") or forward_choice.get("id", "")
            # Pick first perturb param as forward_var_id (best-effort)
            perturb_params = tuple(forward_choice.get("perturb_ib_params") or [])
            forward_var_id = ""
            if perturb_params:
                target_param = perturb_params[0]
                for f in (schema.all_fields if hasattr(schema, "all_fields") else schema.fields):
                    if f.ib_param == target_param:
                        forward_var_id = f.id; break
            report = run_pipeline_ib(
                schema, answers,
                description=desc, forward_var_id=forward_var_id,
                forward_var_name=forward_var_name, delta_pct=delta_pct,
                target_type=schema.subject_kind, mc_iters=800,
                perturb_ib_params=perturb_params,
            )
            # Narrative call
            if llm.get("api_key"):
                try:
                    messages = build_narrative_prompt(
                        desc, answers_to_summary(answers),
                        ib_to_summary(report.ib_inputs),
                        valuation_to_summary(report),
                        archetype_to_summary(report),
                        forward_to_summary(report),
                    )
                    text = call_llm(llm.get("provider",""), llm.get("api_key",""),
                                    llm.get("model",""), messages,
                                    endpoint=llm.get("endpoint",""), max_tokens=4000)
                    narrative = parse_llm_json(text)
                except Exception:
                    narrative = fallback_narrative(report)
            else:
                narrative = fallback_narrative(report)

            rid = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
            SESSION_CACHE[rid] = {"report": report, "narrative": narrative}
            self._json({"id": rid, "narrative": narrative, "report": report.to_dict()})
        except Exception as e:
            self._json({"error": str(e)}, 400)

    def _html(self, html: str, code: int = 200): self._send(html, "text/html; charset=utf-8", code)
    def _json(self, data, code: int = 200):
        self._send(json.dumps(data, ensure_ascii=False, default=str), "application/json; charset=utf-8", code)
    def _send(self, body, content_type: str, code: int = 200):
        if isinstance(body, str): body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers(); self.wfile.write(body)


def _stage_d_shell() -> str:
    """If user navigates to /stage/d directly, restore from localStorage by re-posting compute."""
    return """<main id="d-shell">
<div class="card"><p><span class="spinner" style="border-color:rgba(0,0,0,0.2); border-top-color:var(--rust)"></span> 正在恢复你的报告…</p></div>
</main>
<script>
(function(){
  const sess = window.__store.getActive();
  if (!sess || !sess.dyn_schema) { document.querySelector('main').innerHTML = '<div class="card"><h2>无活动会话</h2><p><a href="/">返回首页</a></p></div>'; return; }
  if (!sess.forward_choice) { location.href = '/stage/f'; return; }
  const cfg = window.__cfg.loadCfg();
  fetch('/api/compute_full', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
    description: sess.description, dyn_schema: sess.dyn_schema, answers: sess.answers || {},
    forward_choice: sess.forward_choice,
    llm: { provider: cfg.provider, api_key: cfg.api_key, model: cfg.model || cfg.custom_model, endpoint: cfg.endpoint },
  })}).then(r => r.json()).then(data => {
    if (data.id) { location.href = '/stage/d?id=' + encodeURIComponent(data.id); }
    else { document.querySelector('main').innerHTML = '<div class="card"><h2>恢复失败</h2><p>'+(data.error||'')+'</p><p><a href="/">返回首页</a></p></div>'; }
  }).catch(e => { document.querySelector('main').innerHTML = '<div class="card"><h2>恢复失败</h2><p>'+e.message+'</p><p><a href="/">返回首页</a></p></div>'; });
})();
</script>"""


def serve(host: str, port: int):
    server = HTTPServer((host, port), Handler)
    print(f"对象/暧昧估值工作台 (v0.3) http://{host}:{port}")
    print("Ctrl-C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止中..."); server.server_close()


def cli_main(args):
    schema = get_fallback_schema()
    answers = {f.id: f.default for f in schema.all_fields}
    report = run_pipeline_ib(schema, answers, description=args.description or "",
                             delta_pct=args.delta_pct, target_type=schema.subject_kind, mc_iters=200)
    out = to_json(report) if args.format == "json" else to_markdown(report, lang="zh")
    if args.out:
        Path(args.out).write_text(out, encoding="utf-8"); print(f"Wrote {args.out}")
    else:
        print(out)


def main():
    p = argparse.ArgumentParser(description="对象/暧昧估值工作台 v0.3")
    p.add_argument("--cli", action="store_true")
    p.add_argument("--description", default="")
    p.add_argument("--delta-pct", type=float, default=0.30)
    p.add_argument("--format", default="markdown", choices=["markdown","json"])
    p.add_argument("--out")
    p.add_argument("--host", default=os.environ.get("VALUATION_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("VALUATION_PORT", "8782")))
    a = p.parse_args()
    if a.cli: cli_main(a)
    else: serve(a.host, a.port)


if __name__ == "__main__":
    main()
