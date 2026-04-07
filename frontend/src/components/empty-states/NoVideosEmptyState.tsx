import { useNavigate } from 'react-router-dom'
import { VideoLibraryIllustration } from './EmptyStateIllustrations'
import { SaaSEmptyState } from './SaaSEmptyState'

type Props = {
  /** Extra action e.g. focus paste field on dashboard */
  onPasteLink?: () => void
  title?: string
  description?: string
}

const DEFAULT_TITLE = 'No videos yet'
const DEFAULT_DESCRIPTION =
  'Paste a YouTube link and run a summarize job. Your recent work will show up here and in History.'

/**
 * Empty state when there are no videos / summaries to show yet.
 */
export function NoVideosEmptyState({
  onPasteLink,
  title = DEFAULT_TITLE,
  description = DEFAULT_DESCRIPTION,
}: Props) {
  const navigate = useNavigate()

  return (
    <SaaSEmptyState
      illustration={<VideoLibraryIllustration />}
      title={title}
      description={description}
      primaryAction={{
        label: 'Summarize a video',
        onClick: () => navigate('/summarize'),
      }}
      secondaryAction={
        onPasteLink
          ? {
              label: 'Paste a link',
              onClick: onPasteLink,
            }
          : undefined
      }
    />
  )
}
