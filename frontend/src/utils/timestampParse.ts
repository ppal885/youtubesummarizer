/** Parse `mm:ss` or `hh:mm:ss` to seconds. Returns null if invalid. */
export function parseTimestampToSeconds(raw: string): number | null {
  const trimmed = raw.trim()
  const parts = trimmed.split(':').map((p) => Number.parseInt(p, 10))
  if (parts.some((n) => !Number.isFinite(n) || n < 0)) return null

  if (parts.length === 2) {
    const [mm, ss] = parts
    if (ss > 59) return null
    return mm * 60 + ss
  }
  if (parts.length === 3) {
    const [hh, mm, ss] = parts
    if (mm > 59 || ss > 59) return null
    return hh * 3600 + mm * 60 + ss
  }
  return null
}

/** Match timestamps wrapped in parentheses, e.g. `(01:23)` or `(1:02:03)`. */
export const PAREN_TIMESTAMP_REGEX = /\((\d{1,2}:\d{2}(?::\d{2})?)\)/g
