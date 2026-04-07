import type { ReactNode } from 'react'

/** Emphasize a short lead (before ":" or first few words) for takeaway bullets. */
export function bulletLeadBold(text: string): ReactNode {
  const trimmed = text.trim()
  const idx = trimmed.indexOf(':')
  if (idx > 0 && idx < 100) {
    return (
      <>
        <strong style={{ fontWeight: 600, color: 'var(--spectrum-gray-900)' }}>{trimmed.slice(0, idx).trim()}</strong>
        <span style={{ color: 'var(--spectrum-gray-700)' }}>:{trimmed.slice(idx + 1)}</span>
      </>
    )
  }
  const words = trimmed.split(/\s+/).filter(Boolean)
  if (words.length <= 3) {
    return <span style={{ color: 'var(--spectrum-gray-700)' }}>{trimmed}</span>
  }
  const lead = words.slice(0, 4).join(' ')
  const rest = words.slice(4).join(' ')
  return (
    <>
      <strong style={{ fontWeight: 600, color: 'var(--spectrum-gray-900)' }}>{lead}</strong>
      {rest ? <span style={{ color: 'var(--spectrum-gray-700)' }}> {rest}</span> : null}
    </>
  )
}
