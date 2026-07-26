// Thin fetch wrappers over the control plane REST API (optimize/dashboard/app.py).
// Every optimizer action the UI can take goes through here — no fetch() elsewhere.

async function j(method, path, body) {
  const opts = { method, headers: {} }
  if (body !== undefined) {
    opts.headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }
  const r = await fetch(path, opts)
  if (!r.ok) throw new Error(`${method} ${path} -> ${r.status}`)
  const ct = r.headers.get('content-type') || ''
  return ct.includes('application/json') ? r.json() : r.text()
}

export const api = {
  // config / status / health
  config: () => j('GET', '/api/config'),
  status: () => j('GET', '/api/status'),
  health: () => j('GET', '/api/health'),

  // planning + lifecycle (run = owned subprocess driver, #28)
  plan: (cfg) => j('POST', '/api/plan', cfg),
  run: (cfg) => j('POST', '/api/run', cfg),
  resume: (cfg) => j('POST', '/api/resume', cfg),
  stop: () => j('POST', '/api/stop'),
  runState: () => j('GET', '/api/run/state'),

  // live progress / ETA (snapshot poll)
  liveProgress: (tf, target) =>
    j('GET', `/api/live/progress?tf=${encodeURIComponent(tf)}&target=${target || 0}`),

  // saved presets
  presets: () => j('GET', '/api/presets'),
  presetSave: (name, cfg) => j('POST', `/api/presets/${encodeURIComponent(name)}`, cfg),
  presetDelete: (name) => j('DELETE', `/api/presets/${encodeURIComponent(name)}`),

  // run queue (instruments × timeframes matrix)
  queueState: () => j('GET', '/api/queue'),
  queueLaunch: (cfg) => j('POST', '/api/queue', cfg),
}

// SSE helper for the legacy log/progress stream (GET /api/progress?tf=...).
export function streamLogs(tf, onLine) {
  const es = new EventSource(`/api/progress?tf=${encodeURIComponent(tf)}`)
  es.onmessage = (e) => {
    try {
      const { line } = JSON.parse(e.data)
      if (line != null) onLine(line)
    } catch { /* ignore malformed frames */ }
  }
  return es
}

// SSE for the OWNED run's live stdout (GET /api/run/logs). onLine per line; onDone at exit.
export function streamRunLogs(onLine, onDone) {
  const es = new EventSource('/api/run/logs')
  es.onmessage = (e) => {
    try {
      const d = JSON.parse(e.data)
      if (d.line != null) onLine(d.line)
      if (d.done) { onDone && onDone(d.returncode); es.close() }
    } catch { /* ignore */ }
  }
  es.onerror = () => es.close()
  return es
}
