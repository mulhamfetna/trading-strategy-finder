/* Shared dashboard engine — included by BOTH index.html (L1) and l2.html (L2).
 * Edit HERE to update both dashboards (DRY). Each page calls DB.initDashboard(cfg) and supplies only
 * its page-specific bits: endpoints, chart panels, params()/setForm()/render(), onConfig(), CSV exports.
 * Everything else (theme, chart scaffolding + time-sync + resize, gutter, inline-math, indicator panel,
 * warmup, strategy dropdown, profile save, dirty/error, run/reset/boot) lives here once. */
(function () {
  const TH = { bg:'#131722', text:'#d1d4dc', border:'#363a45', green:'#00c853', red:'#ff5252',
               blue:'#2962ff', orange:'#ff9800', muted:'#787b86' };
  const COMMON = { layout:{background:{color:TH.bg},textColor:TH.text},
    grid:{vertLines:{color:'#20242f'},horzLines:{color:'#20242f'}},
    timeScale:{timeVisible:true,borderColor:TH.border}, rightPriceScale:{borderColor:TH.border}, crosshair:{mode:0} };
  const $ = id => document.getElementById(id);
  if (typeof window !== 'undefined') window.$ = $;

  const dt = t => new Date(t * 1000).toISOString().slice(0, 16).replace('T', ' ');
  const money = n => (n >= 0 ? '+' : '') + '$' + Math.round(n).toLocaleString();
  const card = (v, k, cls = '') => `<div class="card"><div class="v ${cls}">${v}</div><div class="k">${k}</div></div>`;

  // ── charts: created from a page's panel spec; shared time-sync + resize ──────────────────────
  const charts = [], ctns = [];
  function makeChart(id, h) {
    const el = $(id); const c = LightweightCharts.createChart(el, { ...COMMON, width: el.clientWidth, height: h });
    charts.push(c); ctns.push(el); return c;
  }
  function fitCharts() { charts.forEach((c, i) => { const w = ctns[i].clientWidth; if (w > 0) c.applyOptions({ width: w }); }); }
  function syncCharts() {
    let sy = false;
    charts.forEach(s => s.timeScale().subscribeVisibleTimeRangeChange(r => {
      if (sy || !r) return; sy = true;
      charts.forEach(o => { if (o !== s) { try { o.timeScale().setVisibleRange(r); } catch (e) {} } }); sy = false;
    }));
  }

  function initGutter() {
    const g = $('gutter'), a = document.querySelector('aside'); if (!g || !a) return;
    const CLAMP = w => Math.min(760, Math.max(240, w)); let drag = false;
    try { const sv = +localStorage.getItem('wsi_aside_w'); if (sv) a.style.width = CLAMP(sv) + 'px'; } catch (e) {}
    g.addEventListener('mousedown', e => { drag = true; g.classList.add('drag'); document.body.style.userSelect = 'none'; e.preventDefault(); });
    window.addEventListener('mousemove', e => { if (!drag) return; a.style.width = CLAMP(e.clientX - a.getBoundingClientRect().left) + 'px'; fitCharts(); });
    window.addEventListener('mouseup', () => { if (!drag) return; drag = false; g.classList.remove('drag'); document.body.style.userSelect = '';
      try { localStorage.setItem('wsi_aside_w', parseInt(a.style.width)); } catch (e) {} fitCharts(); });
  }

  // ── inline math in value boxes (type 149.8*1.1) ──────────────────────────────────────────────
  function evalMath(raw) {
    const s = String(raw).trim();
    if (s === '') return { ok: true, val: '' };
    if (/^[0-9.eE\s()+\-*/]+$/.test(s)) {
      try { const v = Function('"use strict";return (' + s + ')')();
        if (typeof v === 'number' && isFinite(v)) return { ok: true, val: v }; } catch (e) {}
    }
    return { ok: false };
  }
  function commitField(el) {
    const r = evalMath(el.value); el.classList.toggle('matherr', !r.ok);
    if (r.ok && r.val !== '' && String(r.val) !== el.value.trim()) { const n = +r.val; el.value = (Number.isInteger(n) ? n : +n.toFixed(6)); }
  }
  function commitMath() { document.querySelectorAll('input.mathnum').forEach(commitField); }
  function mathify(root) {
    (root || document).querySelectorAll('input[type=number]').forEach(el => {
      el.dataset.step = el.getAttribute('step') || ''; el.dataset.min = el.getAttribute('min') || '';
      el.dataset.max = el.getAttribute('max') || ''; el.type = 'text';
      el.setAttribute('inputmode', 'text'); el.setAttribute('autocomplete', 'off'); el.classList.add('mathnum');
    });
  }
  if (typeof document !== 'undefined') {
    document.addEventListener('focusout', e => { const t = e.target; if (t.classList && t.classList.contains('mathnum')) commitField(t); });
    document.addEventListener('keydown', e => { const t = e.target; if (e.key === 'Enter' && t.classList && t.classList.contains('mathnum')) commitField(t); });
  }

  // ── error banner + dirty/clean run-state ─────────────────────────────────────────────────────
  function showErr(msg) { const e = $('err'); if (!e) return; $('errmsg').textContent = msg || ''; e.style.display = msg ? 'block' : 'none';
    if (msg) { try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (_) { window.scrollTo(0, 0); } } }
  let dirty = false;
  function markDirty() { dirty = true; const d = $('dirty'); if (d) { d.textContent = '⚠ not run on these values — click Run'; d.classList.add('stale'); d.classList.remove('ok'); } const r = $('run'); if (r) r.classList.add('stale'); }
  function markClean() { dirty = false; const d = $('dirty'); if (d) { d.textContent = '✓ results match current settings'; d.classList.add('ok'); d.classList.remove('stale'); } const r = $('run'); if (r) r.classList.remove('stale'); }

  // ── indicator panel (built from config.indicator_schema — nothing hardcoded) ─────────────────
  let panelBuilt = false, _warmTimer = null, _warmEndpoint = '/api/warmup';
  function fmtDur(candles) { const m = Math.round(candles), h = Math.floor(m / 60), mm = m % 60; return h ? `${h}h ${mm}m` : `${mm}m`; }
  function recomputeWarmup() {
    clearTimeout(_warmTimer);
    _warmTimer = setTimeout(async () => {
      if (!$('fp_warm') || !$('fp_heavy')) return;
      try {
        const r = await fetch(_warmEndpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ indicators: indicatorSpecs() }) });
        const d = await r.json();
        if (d.error) { $('fp_warm').textContent = '—'; $('fp_heavy').textContent = '(check params)'; return; }
        // measured zero (no indicators enabled) reads as a real value, not missing data ('—').
        // The two cards stay DISTINCT: fp_warm = warmup period, fp_heavy = longest indicator requirement.
        $('fp_warm').textContent = d.max_bars ? `${d.max_bars.toLocaleString()} candles · ${fmtDur(d.max_bars)}` : '0 candles · 0d (no indicators)';
        $('fp_heavy').textContent = d.driver ? `${d.driver.label} — ${d.driver.bars.toLocaleString()} candles · ${fmtDur(d.driver.bars)}` : '0 candles (no indicator requirement)';
      } catch (e) { $('fp_heavy').textContent = 'warmup calc failed'; }
    }, 250);
  }
  // panel-scoped builder — works on ANY host element (the combined dashboard builds two: L1 + L2).
  // onChange (optional) fires on any input; the default single-panel path passes markDirty+warmup.
  function buildPanel(host, sch, onChange) {
    if (!host) return; host.innerHTML = '';
    const modeOpts = sel => sch.modes.map(m => `<option ${m === sel ? 'selected' : ''}>${m}</option>`).join('');
    sch.indicators.forEach(ind => {
      const div = document.createElement('div'); div.className = 'ind'; div.dataset.key = ind.key;
      const pflds = ind.params.map(p => `<div class="fld"><label>${p.name}</label><input class="ind-p" data-p="${p.name}" type="number" step="${p.step}" min="${p.min}" max="${p.max}" value="${p.default}"></div>`).join('');
      div.innerHTML = `<div class="indhead"><label><input type="checkbox" class="ind-en"> ${ind.label}</label>`
        + `<select class="ind-mode" title="confirm / veto / both">${modeOpts(ind.mode)}</select></div><div class="indbody">${pflds}</div>`;
      host.appendChild(div);
      const en = div.querySelector('.ind-en'); en.addEventListener('change', () => div.classList.toggle('on', en.checked));
    });
    if (onChange) host.querySelectorAll('input,select').forEach(el => { el.addEventListener('input', onChange); el.addEventListener('change', onChange); });
    mathify(host);
  }
  // read/write specs for a given host (default = the page's single #indpanel).
  function specsOf(host) {
    host = host || $('indpanel'); const specs = [];
    (host ? host.querySelectorAll('.ind') : []).forEach(el => {
      const p = {}; el.querySelectorAll('.ind-p').forEach(i => p[i.dataset.p] = +i.value);
      specs.push({ key: el.dataset.key, enabled: el.querySelector('.ind-en').checked, mode: el.querySelector('.ind-mode').value, params: p });
    });
    return specs;
  }
  function applySpecsTo(host, specs) {
    if (!specs || !specs.length || !host) return; const by = {}; specs.forEach(s => by[s.key] = s);
    host.querySelectorAll('.ind').forEach(el => {
      const s = by[el.dataset.key]; if (!s) return;
      const en = el.querySelector('.ind-en'); en.checked = !!s.enabled; el.classList.toggle('on', !!s.enabled);
      if (s.mode) el.querySelector('.ind-mode').value = s.mode;
      el.querySelectorAll('.ind-p').forEach(i => { if (s.params && s.params[i.dataset.p] != null) i.value = s.params[i.dataset.p]; });
    });
  }

  // single-panel path (index.html / l2.html): delegates to the host-scoped helpers above (DRY).
  function buildIndicatorPanel(sch) {
    const host = $('indpanel'); if (!host) return;
    buildPanel(host, sch, () => { markDirty(); recomputeWarmup(); });
    if ($('g_retrace_unit') && sch.retrace_units) { $('g_retrace_unit').innerHTML = sch.retrace_units.map(u => `<option ${u === sch.retrace_default.unit ? 'selected' : ''}>${u}</option>`).join('');
      $('g_retrace').value = sch.retrace_default.amount; $('g_wait').value = sch.wait_default; }
    if ($('k_rule')) $('k_rule').value = sch.k_default;
    if (sch.gen_params && $('gen_swing_l')) { const g = {}; sch.gen_params.forEach(p => g[p.name] = p.default); $('gen_swing_l').value = g.swing_l; $('gen_golf_n').value = g.golf_n; }
    panelBuilt = true; recomputeWarmup();
  }
  const indicatorSpecs = () => specsOf($('indpanel'));
  const applyIndicatorSpecs = specs => applySpecsTo($('indpanel'), specs);

  // ── CSV helpers ──────────────────────────────────────────────────────────────────────────────
  function csvEsc(v) { v = (v == null ? '' : String(v)); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
  function toCSV(headers, rows) { return [headers.join(',')].concat(rows.map(r => r.map(csvEsc).join(','))).join('\n'); }
  function downloadCSV(name, text) {
    const blob = new Blob([text], { type: 'text/csv;charset=utf-8' }); const u = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = u; a.download = name; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(u);
  }

  // ── strategy dropdown + profile save (server store + localStorage fallback) ──────────────────
  function buildStrategyDropdown(cfg) {
    const sel = $('strategy'); if (!sel) return;
    window.STRATEGIES = {};
    const srv = window.SERVER_STRATEGIES || [];
    const opt = s => { window.STRATEGIES[s.id] = s.preset; return `<option value="${s.id}">${s.label}</option>`; };
    const builtins = srv.filter(s => !s.id.startsWith('user_'));
    const serverProfiles = srv.filter(s => s.id.startsWith('user_'));
    let html = builtins.map(opt).join('');
    if (serverProfiles.length) html += `<optgroup label="Saved profiles (server)">` + serverProfiles.map(opt).join('') + `</optgroup>`;
    const key = cfg.profileKey || 'wsg_profiles_v1';
    let prof = {}; try { prof = JSON.parse(localStorage.getItem(key)) || {}; } catch (_) {}
    const localNames = Object.keys(prof).filter(n => !serverProfiles.some(s => s.id === 'user_' + n));
    if (localNames.length) html += `<optgroup label="Local only (this browser)">` + localNames.map(n => { const id = 'local_' + n; window.STRATEGIES[id] = prof[n]; return `<option value="${id}">${n}</option>`; }).join('') + `</optgroup>`;
    sel.innerHTML = html;
  }

  // ── the boot/run framework: a page supplies cfg, this wires everything ───────────────────────
  async function initDashboard(cfg) {
    cfg.panels.forEach(p => { const c = makeChart(p.id, p.height); cfg.handles = cfg.handles || {}; cfg.handles[p.id] = { chart: c, series: p.build(c) }; });
    syncCharts();
    window.addEventListener('resize', fitCharts);
    const mainEl = document.querySelector('main'); if (window.ResizeObserver && mainEl) new ResizeObserver(fitCharts).observe(mainEl);
    initGutter();
    if (cfg.warmupEndpoint) _warmEndpoint = cfg.warmupEndpoint;
    mathify(document.querySelector('aside'));
    document.querySelectorAll('aside input,aside select').forEach(el => el.addEventListener('input', markDirty));

    const run = async () => {
      const rb = $('run'); rb.disabled = true; rb.textContent = 'Running...'; status('running…'); showErr('');
      try {
        commitMath();
        const r = await fetch(cfg.endpoints.backtest, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg.params()) });
        let D = null; try { D = await r.json(); } catch (_) {}
        if (!r.ok) throw new Error((D && D.error) ? D.error : ('HTTP ' + r.status));
        if (D && D.error) throw new Error(D.error);
        window.LAST_DATA = D; cfg.render(D, cfg.handles); markClean();
        status(`✓ done${D.meta && D.meta.run_ms ? ' in ' + D.meta.run_ms + ' ms' : ''}`);
      } catch (e) {
        const conn = /Failed to fetch|NetworkError|fetch/i.test(e.message);
        showErr(conn ? 'Cannot reach backend — start server.py then reload.' : `Rejected: ${e.message}`); status('⚠ see error above');
      } finally { rb.disabled = false; rb.textContent = cfg.runLabel || 'Run'; }
    };
    if ($('run')) $('run').addEventListener('click', run);
    if ($('errclose')) $('errclose').addEventListener('click', () => showErr(''));
    if ($('toggle')) $('toggle').addEventListener('click', () => { const hidden = document.body.classList.toggle('no-settings'); $('toggle').textContent = hidden ? '⚙ Show settings' : '⚙ Hide settings'; requestAnimationFrame(fitCharts); });
    if ($('strategy')) $('strategy').addEventListener('change', () => { const p = window.STRATEGIES && window.STRATEGIES[$('strategy').value]; if (!p) return; showErr(''); cfg.setForm(p); markDirty(); status('imported — click Run'); });
    if ($('reset')) $('reset').addEventListener('click', () => { const p = window.STRATEGIES && window.STRATEGIES[$('strategy').value]; if (p) { cfg.setForm(p); markDirty(); status('↺ reset — click Run'); } });
    if ($('saveprofile')) $('saveprofile').addEventListener('click', () => saveProfile(cfg));

    // boot: fetch config, build panel + dropdowns, let the page wire specifics, then default-fill
    try {
      const r = await fetch(cfg.endpoints.config); if (!r.ok) throw new Error('config HTTP ' + r.status);
      const c = await r.json();
      if (c.indicator_schema && !panelBuilt) buildIndicatorPanel(c.indicator_schema);
      if (c.strategies && c.strategies.length) { window.SERVER_STRATEGIES = c.strategies; buildStrategyDropdown(cfg); }
      const def = cfg.onConfig ? cfg.onConfig(c) : null;
      if (def) cfg.setForm(def);
      // auto-fill the form from the currently-selected saved profile so its values are visible on load
      // (fixes "imported profile doesn't fill the boxes"). Opt-in per page via cfg.autoFillSelected.
      else if (cfg.autoFillSelected && $('strategy')) {
        const p = window.STRATEGIES && window.STRATEGIES[$('strategy').value];
        if (p) cfg.setForm(p);
      }
      if (window.WINNER_DATA && cfg.render) { cfg.render(window.WINNER_DATA, cfg.handles); status('showing last saved run · Run for a live run'); }
      else { markDirty(); status('ready · click Run'); }
    } catch (e) { markDirty(); showErr(`Cannot reach backend — start server.py then reload. (${e.message})`); }
  }
  function status(t) { const s = $('status'); if (s) s.innerHTML = t; }

  async function saveProfile(cfg) {
    const name = (prompt('Save current settings as profile named:', 'my profile') || '').trim(); if (!name) return;
    const preset = cfg.params();
    try {
      const r = await fetch(cfg.endpoints.profiles, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, preset }) });
      let d = null; try { d = await r.json(); } catch (_) {}
      if (!r.ok) throw new Error((d && d.error) || ('HTTP ' + r.status));
      if (d && d.strategies) window.SERVER_STRATEGIES = d.strategies;
      else if (d && d.profiles) window.SERVER_STRATEGIES = Object.entries(d.profiles).map(([n, p]) => ({ id: 'user_' + n, label: '👤 ' + n, preset: p }));
      buildStrategyDropdown(cfg); status(`saved “${name}”`);
    } catch (e) {
      const key = cfg.profileKey || 'wsg_profiles_v1'; let prof = {}; try { prof = JSON.parse(localStorage.getItem(key)) || {}; } catch (_) {}
      prof[name] = preset; try { localStorage.setItem(key, JSON.stringify(prof)); } catch (_) {}
      buildStrategyDropdown(cfg); showErr(`Saved “${name}” to THIS BROWSER only — server save failed (${e.message}).`);
    }
  }

  // ── causal log-first view helpers (shared by all three dashboards) ───────────────────────────
  // boxFromLog: append a "· L1/L2" producing-layer tag to an already-formatted value, ONLY when the
  // combined box carries a layer (max-type boxes); sum/recompute boxes carry no layer → no tag.
  function boxFromLog(displayValue, box) {
    return String(displayValue) + (box && box.layer ? ` · ${box.layer}` : '');
  }
  // flatAreaSeries: a per-candle realized-P/L step curve for `layer` — FLAT across bars with no exit,
  // stepping only on that layer's trade exits (the separated views' flat areas). One point per candle.
  function flatAreaSeries(log, layer) {
    const exits = {};
    (log || []).forEach(r => { if (r.layer === layer && r.decision === 'entry' && r.exit_time != null)
      exits[r.exit_time] = (exits[r.exit_time] || 0) + r.pnl; });
    let eq = 0; const out = [];
    (log || []).slice().sort((a, b) => a.time - b.time).forEach(r => {
      if (exits[r.time] != null) eq += exits[r.time];
      out.push({ time: r.time, value: Math.round(eq * 100) / 100 });
    });
    return out;
  }
  // grayMarkers: return a COPY of markers with the grayed ones recolored to the muted theme gray
  // (combined view toggle — never hides, only de-emphasizes). Input is never mutated.
  function grayMarkers(markers, grayed) {
    return (markers || []).map(m => grayed ? { ...m, color: TH.muted } : { ...m });
  }
  // grayLine: gray an equity line IN PLACE without hiding it (never visible:false).
  function grayLine(series, grayed, origColor) {
    if (series && series.applyOptions) series.applyOptions({ color: grayed ? TH.muted : origColor });
  }

  const DB = { TH, COMMON, dt, money, card, makeChart, fitCharts, mathify, commitMath, showErr,
    markDirty, markClean, indicatorSpecs, applyIndicatorSpecs, recomputeWarmup, buildStrategyDropdown,
    buildPanel, specsOf, applySpecsTo, toCSV, downloadCSV, initDashboard, status,
    boxFromLog, flatAreaSeries, grayMarkers, grayLine };
  if (typeof window !== 'undefined') window.DB = DB;
  if (typeof module !== 'undefined' && module.exports) module.exports = DB;   // node test harness
})();
