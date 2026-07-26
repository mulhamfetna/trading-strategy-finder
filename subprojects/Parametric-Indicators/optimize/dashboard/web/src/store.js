import { reactive } from 'vue'
import { api } from './api.js'

// Single reactive store shared by every panel.
//  - `config`  : server-provided bounds/choices/indicator-schema (read-only, from /api/config)
//  - `cfg`     : the run-config the user is assembling (POSTed to /api/plan|run|queue)
//  - `status`  : latest /api/status snapshot (drives button enable-state + health strip)
//  - `conn`    : control-plane connection state for the top bar
export const store = reactive({
  config: {
    samplers: [], engines: [], stage_b: [], timeframes: [], instruments: [],
    bounds: {}, indicators: [], presets: [], trials_per_dim: 0,
  },
  cfg: {
    // selections (all optional — absent keys ⇒ optimizer defaults, byte-identical to a bare launch)
    only_indicators: [], exclude_indicators: [], indicator_mode: 'all', // 'all' | 'only' | 'exclude'
    instruments: [], timeframes: [],
    trials_mode: 'auto', trials: 0, per_trials: {},
    reference: '', max_enabled: null,
    engine: 'single', sampler: '', stage_b: '',
    split_sltp: false, ind_1min: true, cold_start: false, dd_cap: null,
    max_wallclock_min: null,
  },
  status: { ok: false, studies: [] },
  conn: 'connecting', // 'connecting' | 'online' | 'offline'
  loaded: false,

  async loadConfig() {
    try {
      const c = await api.config()
      // config() also embeds a status snapshot under `status`
      this.status = c.status || this.status
      for (const k of ['samplers', 'engines', 'stage_b', 'timeframes', 'instruments',
                       'bounds', 'indicators', 'presets', 'trials_per_dim']) {
        if (c[k] !== undefined) this.config[k] = c[k]
      }
      // sensible first-run defaults derived from the server
      if (!this.cfg.sampler && this.config.samplers.length) this.cfg.sampler = this.config.samplers[0]
      this.conn = 'online'
      this.loaded = true
    } catch (e) {
      this.conn = 'offline'
    }
  },

  async refreshStatus() {
    try {
      this.status = await api.status()
      this.conn = 'online'
    } catch {
      this.conn = 'offline'
    }
  },

  // The subset of cfg actually sent to the backend: strip empty selections so the launch stays
  // byte-identical to a bare optimizer run unless the user opted into something.
  launchCfg() {
    const c = this.cfg
    const out = {
      instruments: c.instruments.length ? c.instruments : undefined,
      timeframes: c.timeframes.length ? c.timeframes : undefined,
      trials_mode: c.trials_mode,
      engine: c.engine, sampler: c.sampler || undefined, stage_b: c.stage_b || undefined,
      split_sltp: c.split_sltp, ind_1min: c.ind_1min, cold_start: c.cold_start,
      reference: c.reference || undefined,
      max_enabled: c.max_enabled || undefined,
      dd_cap: c.dd_cap || undefined,
    }
    if (c.trials_mode === 'one') out.trials = Number(c.trials) || 0
    if (c.trials_mode === 'per') out.per_trials = c.per_trials
    if (c.indicator_mode === 'only' && c.only_indicators.length) out.only_indicators = c.only_indicators
    if (c.indicator_mode === 'exclude' && c.exclude_indicators.length) out.exclude_indicators = c.exclude_indicators
    return out
  },

  // The single-study cfg for the Run button (owned driver): first selected instrument + timeframe.
  runCfg() {
    const c = this.launchCfg()
    c.instrument = this.cfg.instruments[0] || ''
    c.timeframes = this.cfg.timeframes.length ? [this.cfg.timeframes[0]] : []
    c.indicator_mode = this.cfg.indicator_mode
    return c
  },

  // Mandatory fields missing for a run (mirrors runner.validate on the backend) — gates the Run button.
  runMissing() {
    const c = this.runCfg()
    const m = []
    if (!c.instrument) m.push('instrument')
    if (!c.timeframes.length) m.push('timeframe')
    if (c.trials_mode === 'one' && !(Number(c.trials) > 0)) m.push('trials count')
    if (this.cfg.indicator_mode === 'only' && !this.cfg.only_indicators.length) m.push('≥1 indicator (only)')
    if (this.cfg.indicator_mode === 'exclude' && !this.cfg.exclude_indicators.length) m.push('≥1 indicator (exclude)')
    return m
  },
})
