import { apiBase } from './client'
import type { AskRequestBody, AskResponse } from './types'

export type AskStreamHandlers = {
  onDelta: (text: string) => void
  onDone: (response: AskResponse) => void
  onError: (message: string) => void
}

/**
 * POST /api/v1/ask with ``Accept: text/event-stream`` — progressive token deltas, then a final ``done`` event.
 * Same SSE contract as ``POST /api/v1/ask/stream`` (kept for explicit clients).
 * Parses ``data:`` JSON payloads; buffers incomplete events until a full ``\\n\\n`` block.
 */
export async function postAskStream(
  body: AskRequestBody,
  handlers: AskStreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const path = '/api/v1/ask'
  const url = `${apiBase()}${path.startsWith('/') ? path : `/${path}`}`
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok) {
    const text = await res.text()
    let detail = text
    try {
      const j = JSON.parse(text) as { detail?: unknown }
      if (typeof j.detail === 'string') detail = j.detail
    } catch {
      /* keep text */
    }
    handlers.onError(detail || `HTTP ${res.status}`)
    return
  }

  const reader = res.body?.getReader()
  if (!reader) {
    handlers.onError('No response body to read')
    return
  }

  const decoder = new TextDecoder()
  let buffer = ''

  const processBlock = (block: string) => {
    const lines = block.split('\n')
    for (const line of lines) {
      if (!line.startsWith('data:')) continue
      const raw = line.startsWith('data: ') ? line.slice(6) : line.slice(5)
      const payload = raw.trim()
      if (!payload) continue
      let parsed: Record<string, unknown>
      try {
        parsed = JSON.parse(payload) as Record<string, unknown>
      } catch {
        handlers.onError('Malformed stream data (invalid JSON)')
        return
      }
      const t = parsed.type
      if (t === 'delta' && typeof parsed.text === 'string') {
        handlers.onDelta(parsed.text)
      } else if (t === 'done') {
        const answer = typeof parsed.answer === 'string' ? parsed.answer : ''
        const confidence = typeof parsed.confidence === 'number' ? parsed.confidence : 0
        const sources = Array.isArray(parsed.sources) ? parsed.sources : []
        handlers.onDone({
          answer,
          confidence,
          sources: sources as AskResponse['sources'],
        })
      } else if (t === 'error' && typeof parsed.message === 'string') {
        handlers.onError(parsed.message)
      }
    }
  }

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parts = buffer.split('\n\n')
      buffer = parts.pop() ?? ''
      for (const block of parts) {
        if (block.trim()) processBlock(block)
      }
    }
    if (buffer.trim()) processBlock(buffer)
  } catch (e) {
    if (signal?.aborted) return
    handlers.onError(e instanceof Error ? e.message : String(e))
  }
}
