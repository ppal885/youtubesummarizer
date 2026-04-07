import type { CSSProperties } from 'react'

type Props = {
  label: string
  seconds: number | null
  onSeek: (seconds: number) => void
}

const linkStyle: CSSProperties = {
  display: 'inline',
  cursor: 'pointer',
  border: 'none',
  padding: 0,
  background: 'none',
  font: 'inherit',
  fontWeight: 600,
  color: 'var(--spectrum-blue-800)',
  textDecoration: 'underline',
  textUnderlineOffset: 2,
}

export function TimestampLink({ label, seconds, onSeek }: Props) {
  if (seconds == null) {
    return <span style={{ color: 'var(--spectrum-gray-800)' }}>{label}</span>
  }

  return (
    <button type="button" onClick={() => onSeek(seconds)} style={linkStyle} title={`Jump to ${label}`}>
      {label}
    </button>
  )
}
