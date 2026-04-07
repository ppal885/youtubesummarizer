import { Flex, Grid, Heading, Text, View } from '@adobe/react-spectrum'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { postAskStream } from '../api/streamAsk'
import type { AskRequestBody } from '../api/types'
import { ChatComposer } from '../components/ChatComposer'
import { CHAT_COMPOSER_INPUT_ID } from '../components/empty-states'
import { ChatMessageList } from '../components/ChatMessageList'
import type { ChatMessage } from '../components/chatTypes'
import { SuggestedQuestions } from '../components/SuggestedQuestions'
import { VideoUrlActionBar } from '../components/VideoUrlActionBar'
import { VideoPlayer, type VideoPlayerHandle } from '../components/VideoPlayer'
import { useAppConfig } from '../context/AppConfigContext'
import { incrementQuestionsAsked } from '../dashboard/usageStorage'
import { DEFAULT_LANGUAGE, FALLBACK_VIDEO_URL } from '../lib/defaults'
import workspace from '../styles/workspacePage.module.css'
import { buildAskAiDisplayItems } from '../utils/suggestedQuestions'
import { extractYouTubeVideoId } from '../utils/youtube'
import askAiStyles from './AskAiPage.module.css'

type RouteState = {
  url?: string
  question?: string
}

function createMessageId() {
  return crypto.randomUUID()
}

type ChatLayout = 'compact' | 'mid' | 'full'

function readChatLayout(): ChatLayout {
  if (typeof window === 'undefined') return 'compact'
  const w = window.innerWidth
  if (w >= 1024) return 'full'
  if (w >= 640) return 'mid'
  return 'compact'
}

export function AskAiPage() {
  const location = useLocation()
  const routeState = (location.state as RouteState | null) ?? null
  const { defaultVideoUrl } = useAppConfig()
  const [url, setUrl] = useState(routeState?.url || defaultVideoUrl)
  const [chatDraft, setChatDraft] = useState(routeState?.question || '')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [error, setError] = useState<string | null>(null)
  const [chatSending, setChatSending] = useState(false)
  const [streamHasBubble, setStreamHasBubble] = useState(false)
  const [chatLayout, setChatLayout] = useState<ChatLayout>(() => readChatLayout())
  const streamingAssistantIdRef = useRef<string | null>(null)
  const videoPlayerRef = useRef<VideoPlayerHandle>(null)

  useEffect(() => {
    const onResize = () => setChatLayout(readChatLayout())
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  useEffect(() => {
    setUrl((current) => {
      if (routeState?.url) return routeState.url
      return current === FALLBACK_VIDEO_URL || current === '' ? defaultVideoUrl : current
    })
  }, [defaultVideoUrl, routeState?.url])

  useEffect(() => {
    if (routeState?.question) {
      setChatDraft(routeState.question)
    }
  }, [routeState?.question])

  const previewVideoId = extractYouTubeVideoId(url.trim())

  const suggestedChips = useMemo(
    () => buildAskAiDisplayItems(routeState?.question),
    [routeState?.question],
  )

  const runAskStream = useCallback(
    async (trimmedUrl: string, trimmedQuestion: string, opts: { appendUser: boolean }) => {
      const videoId = extractYouTubeVideoId(trimmedUrl)
      if (!videoId) {
        setError('Enter a valid YouTube URL before asking the assistant.')
        return
      }

      const q = trimmedQuestion.trim()
      if (!q) {
        return
      }

      setError(null)
      if (opts.appendUser) {
        setMessages((current) => [
          ...current,
          { id: createMessageId(), role: 'user', content: q, createdAt: Date.now() },
        ])
      }

      setChatSending(true)
      setStreamHasBubble(false)
      streamingAssistantIdRef.current = null

      const body: AskRequestBody = {
        url: trimmedUrl,
        question: q,
        language: DEFAULT_LANGUAGE,
      }

      try {
        await postAskStream(body, {
          onDelta(text) {
            setStreamHasBubble(true)
            setMessages((current) => {
              const streamingId = streamingAssistantIdRef.current
              if (!streamingId) {
                const nextId = createMessageId()
                streamingAssistantIdRef.current = nextId
                return [...current, { id: nextId, role: 'assistant', content: text, isStreaming: true }]
              }

              return current.map((message) =>
                message.id === streamingId ? { ...message, content: message.content + text } : message,
              )
            })
          },
          onDone(response) {
            const answer = response.answer.trim() || '(Empty answer)'
            const streamingId = streamingAssistantIdRef.current
            const finishedAt = Date.now()
            setMessages((current) => {
              if (!streamingId) {
                return [
                  ...current,
                  {
                    id: createMessageId(),
                    role: 'assistant',
                    content: answer,
                    confidence: response.confidence,
                    sources: response.sources,
                    createdAt: finishedAt,
                  },
                ]
              }

              return current.map((message) =>
                message.id === streamingId
                  ? {
                      ...message,
                      content: answer,
                      confidence: response.confidence,
                      sources: response.sources,
                      isStreaming: false,
                      createdAt: finishedAt,
                    }
                  : message,
              )
            })
            streamingAssistantIdRef.current = null
            incrementQuestionsAsked()
          },
          onError(message) {
            const friendly = `Sorry, something went wrong: ${message}`
            const failedAt = Date.now()
            setError(friendly)
            const streamingId = streamingAssistantIdRef.current
            setMessages((current) => {
              if (!streamingId) {
                return [
                  ...current,
                  {
                    id: createMessageId(),
                    role: 'assistant',
                    content: friendly,
                    createdAt: failedAt,
                  },
                ]
              }

              return current.map((message) =>
                message.id === streamingId
                  ? { ...message, content: friendly, isStreaming: false, createdAt: failedAt }
                  : message,
              )
            })
            streamingAssistantIdRef.current = null
          },
        })
      } catch (err) {
        const friendly = err instanceof Error ? err.message : String(err)
        setError(friendly)
        setMessages((current) => [
          ...current,
          {
            id: createMessageId(),
            role: 'assistant',
            content: `Sorry, something went wrong: ${friendly}`,
            createdAt: Date.now(),
          },
        ])
      } finally {
        setChatSending(false)
        setStreamHasBubble(false)
        if (opts.appendUser) {
          setChatDraft('')
        }
      }
    },
    [],
  )

  async function sendQuestion(question: string) {
    if (chatSending) return
    await runAskStream(url.trim(), question, { appendUser: true })
  }

  const regenerateAssistant = useCallback(
    (assistantMessageId: string) => {
      if (chatSending) return
      const idx = messages.findIndex((m) => m.id === assistantMessageId)
      if (idx < 1) return
      const prev = messages[idx - 1]
      if (prev.role !== 'user') return
      const userText = prev.content
      setMessages((c) => c.slice(0, idx))
      void runAskStream(url.trim(), userText, { appendUser: false })
    },
    [chatSending, messages, runAskStream, url],
  )

  return (
    <Flex direction="column" gap="size-300">
      <View
        padding="size-300"
        borderRadius="medium"
        borderWidth="thin"
        borderColor="blue-500"
        backgroundColor="static-blue-200"
      >
        <VideoUrlActionBar
          label="Ask AI"
          description="Stream grounded answers while staying inside the workspace shell."
          url={url}
          onUrlChange={setUrl}
          onSubmit={() => void sendQuestion(chatDraft)}
          actionLabel="Send prompt"
          busyLabel="Thinking..."
          busy={chatSending}
        />
        {error ? (
          <View
            marginTop="size-200"
            padding="size-200"
            borderRadius="medium"
            borderWidth="thin"
            borderColor="negative"
            backgroundColor="gray-75"
          >
            <Text UNSAFE_className={workspace.errorText}>{error}</Text>
          </View>
        ) : null}
      </View>

      <Grid columns={{ base: '1fr', L: '1fr 1fr', XL: '1.05fr 1.15fr' }} gap="size-300" alignItems="stretch">
        <Flex direction="column" gap="size-300" order={{ base: 2, L: 1 }}>
          <View borderRadius="medium" overflow="hidden" borderWidth="thin" borderColor="gray-300" backgroundColor="gray-900">
            <View UNSAFE_className={workspace.videoAspect16x9}>
              <VideoPlayer ref={videoPlayerRef} videoId={previewVideoId} />
            </View>
          </View>

          <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
            <Text UNSAFE_className={workspace.sectionLabel}>STARTER PROMPTS</Text>
            <View marginTop="size-200">
              <SuggestedQuestions
                items={suggestedChips}
                instantSend
                disabled={chatSending}
                onSelect={(question) => {
                  setChatDraft(question)
                  void sendQuestion(question)
                }}
              />
            </View>
          </View>
        </Flex>

        <Flex direction="column" order={{ base: 1, L: 2 }} minHeight={0}>
          <View
            flex={1}
            minHeight={0}
            padding="size-250"
            borderRadius="medium"
            borderWidth="thin"
            borderColor="gray-200"
            backgroundColor="gray-50"
            UNSAFE_className={askAiStyles.conversationShell}
          >
            <View marginBottom="size-100" flexShrink={0}>
              <Text UNSAFE_className={workspace.sectionLabel}>CONVERSATION</Text>
              <Heading level={2} marginTop="size-100">
                Ask about the current video
              </Heading>
            </View>

            <View
              flex={1}
              minHeight={0}
              padding="size-150"
              borderRadius="medium"
              backgroundColor="gray-75"
              UNSAFE_className={askAiStyles.conversationScrollHost}
            >
              <ChatMessageList
                messages={messages}
                showTyping={chatSending && !streamHasBubble}
                composerInputId={CHAT_COMPOSER_INPUT_ID}
                chatSending={chatSending}
                onRegenerateAssistant={regenerateAssistant}
                onTimestampSeek={(seconds) => videoPlayerRef.current?.seekTo(seconds)}
                scrollLayout={chatLayout}
              />
            </View>

            <View marginTop="size-100" flexShrink={0}>
              <ChatComposer
                id={CHAT_COMPOSER_INPUT_ID}
                value={chatDraft}
                onChange={setChatDraft}
                onSend={() => void sendQuestion(chatDraft)}
                disabled={!previewVideoId}
                sending={chatSending}
                placeholder="Ask the assistant about this video..."
              />
            </View>
          </View>
        </Flex>
      </Grid>
    </Flex>
  )
}
