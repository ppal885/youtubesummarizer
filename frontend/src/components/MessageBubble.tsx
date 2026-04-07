import { Button, Flex, Text, View } from '@adobe/react-spectrum'
import { useCallback, useState } from 'react'
import type { AskSource } from '../api/types'
import { TextWithTimestamps } from './TextWithTimestamps'

type Role = 'user' | 'assistant'

type Props = {
  role: Role
  content: string
  createdAt?: number
  onTimestampSeek?: (seconds: number) => void
  confidence?: number
  sources?: AskSource[]
  isStreaming?: boolean
  onRegenerate?: () => void
  showRegenerate?: boolean
  regenerateDisabled?: boolean
}

function formatMessageTime(ts: number | undefined): string | null {
  if (ts == null) return null
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: 'numeric',
      minute: '2-digit',
    }).format(new Date(ts))
  } catch {
    return null
  }
}

function buildCopyText(content: string, sources: AskSource[] | undefined): string {
  if (!sources?.length) return content
  const lines = sources.map((s) => `${s.formatted_time}  ${s.text}`)
  return `${content}\n\nSources:\n${lines.join('\n')}`
}

export function MessageBubble({
  role,
  content,
  createdAt,
  onTimestampSeek,
  confidence,
  sources,
  isStreaming,
  onRegenerate,
  showRegenerate,
  regenerateDisabled,
}: Props) {
  const isUser = role === 'user'
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async () => {
    const text = buildCopyText(content, isUser ? undefined : sources)
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }, [content, sources, isUser])

  const timeLabel = formatMessageTime(createdAt)

  const bubbleBg = isUser ? 'gray-900' : 'gray-50'
  const bubbleBorder = isUser ? 'gray-900' : 'gray-200'

  return (
    <Flex direction="column" alignItems={isUser ? 'end' : 'start'} width="100%">
      <View
        maxWidth="size-6000"
        padding="size-200"
        borderRadius="medium"
        borderWidth="thin"
        borderColor={bubbleBorder}
        backgroundColor={bubbleBg}
        UNSAFE_style={
          isUser
            ? { borderBottomRightRadius: 6 }
            : { borderBottomLeftRadius: 6, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }
        }
      >
        <Flex
          direction="row"
          gap="size-50"
          marginBottom="size-100"
          justifyContent={isUser ? 'end' : 'start'}
          wrap
        >
          <Button variant="secondary" isQuiet onPress={() => void handleCopy()}>
            {copied ? 'Copied' : 'Copy'}
          </Button>
          {!isUser && showRegenerate && onRegenerate ? (
            <Button
              variant="secondary"
              isQuiet
              onPress={onRegenerate}
              isDisabled={regenerateDisabled || isStreaming}
            >
              Regenerate
            </Button>
          ) : null}
        </Flex>

        <View>
          {isUser || !onTimestampSeek ? (
            <Text UNSAFE_style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: isUser ? '#fff' : undefined }}>
              {content}
              {!isUser && isStreaming ? (
                <span
                  className="message-streaming-caret"
                  style={{
                    marginLeft: 2,
                    display: 'inline-block',
                    width: 2,
                    height: 14,
                    verticalAlign: '-3px',
                    background: 'var(--spectrum-gray-500)',
                    animation: 'message-caret-pulse 1s ease-in-out infinite',
                  }}
                  aria-hidden
                />
              ) : null}
            </Text>
          ) : (
            <p style={{ margin: 0 }}>
              <TextWithTimestamps text={content} onSeek={onTimestampSeek} />
              {isStreaming ? (
                <span
                  className="message-streaming-caret"
                  style={{
                    marginLeft: 2,
                    display: 'inline-block',
                    width: 2,
                    height: 14,
                    verticalAlign: '-3px',
                    background: 'var(--spectrum-gray-500)',
                    animation: 'message-caret-pulse 1s ease-in-out infinite',
                  }}
                  aria-hidden
                />
              ) : null}
            </p>
          )}
        </View>

        {!isUser && !isStreaming && confidence !== undefined ? (
          <Text UNSAFE_style={{ marginTop: 8, fontSize: 11, fontWeight: 500, color: 'var(--spectrum-gray-600)' }}>
            Confidence {Math.round(confidence * 100)}%
          </Text>
        ) : null}

        {!isUser && !isStreaming && sources?.length && onTimestampSeek ? (
          <View
            marginTop="size-150"
            paddingTop="size-150"
            borderTopWidth="thin"
            borderTopColor="gray-200"
          >
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {sources.map((s, i) => (
                <li key={`${s.start_time}-${i}`}>
                  <Button
                    variant="secondary"
                    isQuiet
                    width="100%"
                    onPress={() => onTimestampSeek(s.start_time)}
                    UNSAFE_style={{ justifyContent: 'flex-start', minHeight: 'auto', padding: '6px 4px' }}
                  >
                    <Text UNSAFE_style={{ textAlign: 'left', fontSize: 11, lineHeight: 1.4 }}>
                      <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{s.formatted_time}</span>
                      <span style={{ marginLeft: 6 }}>{s.text}</span>
                    </Text>
                  </Button>
                </li>
              ))}
            </ul>
          </View>
        ) : null}
      </View>

      {timeLabel ? (
        <time
          dateTime={createdAt != null ? new Date(createdAt).toISOString() : undefined}
          style={{
            marginTop: 4,
            paddingLeft: 4,
            paddingRight: 4,
            fontSize: 10,
            fontWeight: 500,
            fontVariantNumeric: 'tabular-nums',
            color: 'var(--spectrum-gray-500)',
            textAlign: isUser ? 'right' : 'left',
            width: '100%',
            maxWidth: 'min(92%, 28rem)',
          }}
        >
          {timeLabel}
        </time>
      ) : null}
    </Flex>
  )
}
