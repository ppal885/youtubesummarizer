import type { ReactNode } from 'react'
import { PAREN_TIMESTAMP_REGEX, parseTimestampToSeconds } from '../utils/timestampParse'
import { TimestampLink } from './TimestampLink'

type Props = {
  text: string
  onSeek: (seconds: number) => void
}

/**
 * Renders plain text with `(mm:ss)` / `(h:mm:ss)` segments as clickable seek controls.
 */
export function TextWithTimestamps({ text, onSeek }: Props) {
  const nodes: ReactNode[] = []
  let last = 0
  const re = new RegExp(PAREN_TIMESTAMP_REGEX.source, PAREN_TIMESTAMP_REGEX.flags)
  let match: RegExpExecArray | null

  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      nodes.push(text.slice(last, match.index))
    }
    const inner = match[1] ?? ''
    const seconds = parseTimestampToSeconds(inner)
    const label = match[0]
    nodes.push(
      <TimestampLink key={`${match.index}-${label}`} label={label} seconds={seconds} onSeek={onSeek} />,
    )
    last = re.lastIndex
  }

  if (last < text.length) {
    nodes.push(text.slice(last))
  }

  return (
    <span style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', lineHeight: 1.6 }}>{nodes}</span>
  )
}
