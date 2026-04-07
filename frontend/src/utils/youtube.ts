/** Client-side video id for embed; backend still validates on summarize. */
export function extractYouTubeVideoId(input: string): string | null {
  const raw = input.trim()
  if (!raw) return null
  try {
    const u = new URL(raw.startsWith('http') ? raw : `https://${raw}`)
    const host = u.hostname.replace(/^www\./, '')
    if (host === 'youtu.be') {
      const id = u.pathname.split('/').filter(Boolean)[0]
      return id && /^[\w-]{11}$/.test(id) ? id : null
    }
    if (host.endsWith('youtube.com') || host.endsWith('youtube-nocookie.com')) {
      if (u.pathname.startsWith('/watch')) {
        const v = u.searchParams.get('v')
        return v && /^[\w-]{11}$/.test(v) ? v : null
      }
      const m = u.pathname.match(/^\/embed\/([\w-]{11})/)
      if (m) return m[1]
      const s = u.pathname.match(/^\/shorts\/([\w-]{11})/)
      if (s) return s[1]
    }
  } catch {
    /* invalid URL */
  }
  return null
}
