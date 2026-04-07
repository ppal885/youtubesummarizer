import { Badge } from '@adobe/react-spectrum'
import type { SummaryJobState } from '../../api/types'

type Props = {
  status: SummaryJobState
}

const variantByStatus: Record<
  SummaryJobState,
  'neutral' | 'info' | 'positive' | 'negative' | 'yellow'
> = {
  queued: 'yellow',
  running: 'info',
  completed: 'positive',
  failed: 'negative',
}

export function StatusPill({ status }: Props) {
  return (
    <Badge variant={variantByStatus[status]} UNSAFE_style={{ textTransform: 'capitalize' }}>
      {status}
    </Badge>
  )
}
