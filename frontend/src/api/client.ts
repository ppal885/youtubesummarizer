/** API base: empty uses Vite dev proxy to FastAPI; set VITE_API_BASE for direct calls (e.g. production). */
export function apiBase(): string {
  const raw = import.meta.env.VITE_API_BASE as string | undefined
  if (raw == null || String(raw).trim() === '') {
    return ''
  }
  return String(raw).replace(/\/$/, '')
}

export async function apiJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = `${apiBase()}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
  const text = await res.text()
  if (!res.ok) {
    let detail = text
    try {
      const j = JSON.parse(text) as { detail?: unknown }
      if (typeof j.detail === 'string') {
        detail = j.detail
      }
    } catch {
      /* keep text */
    }
    throw new Error(detail || `HTTP ${res.status}`)
  }
  if (!text) {
    return undefined as T
  }
  return JSON.parse(text) as T
}
