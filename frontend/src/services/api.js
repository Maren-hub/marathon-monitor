const API_BASE = import.meta.env.VITE_API_BASE ?? ''

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
    ...options
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `请求失败：${response.status}`)
  }
  return response.json()
}

export const platformApi = {
  snapshot: () => request('/api/snapshot'),
  analytics: () => request('/api/analytics'),
  campusRoute: () => request('/api/campus-route'),
  models: () => request('/api/models'),
  modelJob: (id) => request(`/api/models/jobs/${encodeURIComponent(id)}`),
  importModel: (file, onProgress = () => {}) => new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    const params = new URLSearchParams({ filename: file.name })
    xhr.open('POST', `${API_BASE}/api/models/import?${params}`)
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100))
    }
    xhr.onerror = () => reject(new Error('上传连接中断，请确认前后端都在运行'))
    xhr.onload = () => {
      let payload
      try { payload = JSON.parse(xhr.responseText) } catch { payload = {} }
      if (xhr.status >= 200 && xhr.status < 300) resolve(payload)
      else reject(new Error(payload.detail ?? `上传失败：${xhr.status}`))
    }
    xhr.send(file)
  }),
  importCampusGeoJson: async (file, kind) => {
    const params = new URLSearchParams({ filename: file.name, kind })
    const response = await fetch(`${API_BASE}/api/campus-route/import?${params}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/geo+json' },
      body: file
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.detail ?? `导入失败：${response.status}`)
    return payload
  },
  pipelineSegments: () => request('/api/pipeline/segments'),
  pipelineStatus: () => request('/api/pipeline/status'),
  pipelineSourceRecords: (source, limit = 200) =>
    request(`/api/pipeline/sources/${encodeURIComponent(source)}/records?limit=${limit}`),
  pipelineRules: () => request('/api/pipeline/rules'),
  resetPipeline: () => request('/api/pipeline/reset', { method: 'POST' }),
  resetPipelineSource: (source) =>
    request(`/api/pipeline/sources/${encodeURIComponent(source)}/reset`, { method: 'POST' }),
  importSpreadsheet: async (file, defaultStatus = '模拟', expectedKind = '') => {
    const params = new URLSearchParams({ filename: file.name, default_status: defaultStatus })
    if (expectedKind) params.set('expected_kind', expectedKind)
    const response = await fetch(`${API_BASE}/api/pipeline/import-file?${params}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/octet-stream' },
      body: file
    })
    const payload = await response.json()
    if (!response.ok) {
      const error = new Error(payload.detail?.message ?? '表格导入失败')
      error.issues = payload.detail?.issues ?? []
      throw error
    }
    return payload
  },
  injectEvent: (eventType, segmentId) =>
    request('/api/simulation/events', {
      method: 'POST',
      body: JSON.stringify({ event_type: eventType, segment_id: segmentId })
    }),
  control: (action) =>
    request('/api/simulation/control', {
      method: 'POST',
      body: JSON.stringify({ action })
    }),
  acknowledge: (alertId) =>
    request(`/api/alerts/${alertId}/acknowledge`, { method: 'POST' }),
  alertAction: (alertId, action) =>
    request(`/api/alerts/${alertId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action })
    }),
  exportResults: async (mode = 'simulation') => {
    const response = await fetch(`${API_BASE}/api/export?mode=${encodeURIComponent(mode)}`)
    if (!response.ok) throw new Error(await response.text())
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = response.headers.get('Content-Disposition')?.match(/filename="?([^";]+)/)?.[1] ?? 'zhihui-run-export.zip'
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
}

export function liveSocketUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/live`
}
