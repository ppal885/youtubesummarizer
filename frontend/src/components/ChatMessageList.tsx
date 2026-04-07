import { Flex, Text, View } from '@adobe/react-spectrum'
import { useEffect, useRef } from 'react'
import type { ChatMessage } from './chatTypes'
import chatScroll from './chat/chatScroll.module.css'
import { CHAT_COMPOSER_INPUT_ID, NoChatHistoryEmptyState } from './empty-states'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'

export type ChatScrollLayout = 'compact' | 'mid' | 'full'

type Props = {
  messages: ChatMessage[]
  showTyping?: boolean
  emptyDescription?: string
  composerInputId?: string
  onTimestampSeek?: (seconds: number) => void
  chatSending?: boolean
  onRegenerateAssistant?: (assistantMessageId: string) => void
  /** Responsive max-height preset for the scrollable message region. */
  scrollLayout?: ChatScrollLayout
}

function scrollLayoutClass(layout: ChatScrollLayout | undefined) {
  if (layout === 'full') return chatScroll.scrollFull
  if (layout === 'mid') return chatScroll.scrollMid
  if (layout === 'compact') return chatScroll.scrollCompact
  return chatScroll.scrollDefault
}

export function ChatMessageList({
  messages,
  showTyping,
  emptyDescription,
  composerInputId = CHAT_COMPOSER_INPUT_ID,
  onTimestampSeek,
  chatSending,
  onRegenerateAssistant,
  scrollLayout,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
  }, [messages, showTyping])

  return (
    <Flex direction="column" flex={1} minHeight={0} minWidth={0}>
      <Text UNSAFE_className={chatScroll.chatSectionLabel}>CHAT</Text>
      <div ref={scrollRef} className={`${chatScroll.scrollRoot} ${scrollLayoutClass(scrollLayout)}`}>
        {messages.length === 0 && !showTyping ? (
          <NoChatHistoryEmptyState
            composerInputId={composerInputId}
            {...(emptyDescription ? { description: emptyDescription } : {})}
          />
        ) : null}
        <Flex direction="column" gap="size-200" UNSAFE_className={chatScroll.messagesColumn}>
          {messages.map((m, index) => {
            const prev = index > 0 ? messages[index - 1] : null
            const canRegenerate =
              m.role === 'assistant' &&
              Boolean(prev && prev.role === 'user') &&
              !m.isStreaming &&
              Boolean(onRegenerateAssistant)

            return (
              <MessageBubble
                key={m.id}
                role={m.role}
                content={m.content}
                createdAt={m.createdAt}
                onTimestampSeek={m.role === 'assistant' ? onTimestampSeek : undefined}
                confidence={m.role === 'assistant' ? m.confidence : undefined}
                sources={m.role === 'assistant' ? m.sources : undefined}
                isStreaming={m.role === 'assistant' ? m.isStreaming : undefined}
                showRegenerate={canRegenerate}
                onRegenerate={
                  canRegenerate && onRegenerateAssistant ? () => onRegenerateAssistant(m.id) : undefined
                }
                regenerateDisabled={chatSending}
              />
            )
          })}
          {showTyping ? (
            <View>
              <TypingIndicator />
            </View>
          ) : null}
          <div ref={bottomRef} style={{ height: 1, flexShrink: 0 }} aria-hidden />
        </Flex>
      </div>
    </Flex>
  )
}
