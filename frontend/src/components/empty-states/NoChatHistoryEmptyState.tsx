import { View } from '@adobe/react-spectrum'
import { ChatThreadsIllustration } from './EmptyStateIllustrations'
import { SaaSEmptyState } from './SaaSEmptyState'

const DEFAULT_COMPOSER_ID = 'copilot-chat-composer'

const DEFAULT_DESCRIPTION =
  'Ask grounded questions about the video. Answers stream in with citations you can jump to in the player.'

type Props = {
  composerInputId?: string
  primaryLabel?: string
  description?: string
  onPrimaryAction?: () => void
}

function focusComposer(id: string) {
  const el = document.getElementById(id)
  if (el instanceof HTMLElement) {
    el.focus()
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }
}

export function NoChatHistoryEmptyState({
  composerInputId = DEFAULT_COMPOSER_ID,
  primaryLabel = 'Write a message',
  description = DEFAULT_DESCRIPTION,
  onPrimaryAction,
}: Props) {
  return (
    <View paddingY="size-300">
      <SaaSEmptyState
        illustration={<ChatThreadsIllustration />}
        title="No chat history yet"
        description={description}
        primaryAction={{
          label: primaryLabel,
          onClick: onPrimaryAction ?? (() => focusComposer(composerInputId)),
        }}
      />
    </View>
  )
}

export { DEFAULT_COMPOSER_ID as CHAT_COMPOSER_INPUT_ID }
