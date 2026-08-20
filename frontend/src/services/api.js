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
    })
}

export function liveSocketUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/live`
}
