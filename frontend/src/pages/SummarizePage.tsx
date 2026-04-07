import { Badge, Flex, Grid, Heading, Item, Picker, Text, View } from '@adobe/react-spectrum'
import type { ReactNode } from 'react'
import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { apiJson } from '../api/client'
import type {
  FinalSummary,
  SummaryJobAcceptedResponse,
  SummaryJobState,
  SummaryJobStatusResponse,
  SummaryType,
} from '../api/types'
import {
  ChaptersSkeleton,
  KeyMomentsSkeleton,
  SuggestedFollowUpsSkeleton,
} from '../components/loading'
import { SuggestedQuestions } from '../components/SuggestedQuestions'
import { SummaryPanel } from '../components/SummaryPanel'
import { VideoUrlActionBar } from '../components/VideoUrlActionBar'
import { VideoPlayer } from '../components/VideoPlayer'
import { StatusPill } from '../components/ui/StatusPill'
import { useAppConfig } from '../context/AppConfigContext'
import { incrementVideosProcessed, prependRecentVideo } from '../dashboard/usageStorage'
import { DEFAULT_LANGUAGE, FALLBACK_VIDEO_URL } from '../lib/defaults'
import {
  buildSuggestedQuestions,
  categorizePlainQuestionStrings,
  type SuggestedQuestionItem,
} from '../utils/suggestedQuestions'
import workspace from '../styles/workspacePage.module.css'
import { extractYouTubeVideoId } from '../utils/youtube'

const summaryTypeOptions: SummaryType[] = ['brief', 'bullet', 'detailed', 'technical']

function wait(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

function sectionCard(children: ReactNode) {
  return <View UNSAFE_className={workspace.sectionCard}>{children}</View>
}

export function SummarizePage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { defaultVideoUrl, demoMode } = useAppConfig()
  const [url, setUrl] = useState(defaultVideoUrl)
  const [summaryType, setSummaryType] = useState<SummaryType>('bullet')
  const [summary, setSummary] = useState<FinalSummary | null>(null)
  const [suggestedQuestions, setSuggestedQuestions] = useState<SuggestedQuestionItem[]>([])
  const [activeVideoId, setActiveVideoId] = useState<string | null>(extractYouTubeVideoId(defaultVideoUrl))
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<SummaryJobState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isMountedRef = useRef(true)
  const appliedWorkspaceNav = useRef(false)

  useEffect(() => {
    return () => {
      isMountedRef.current = false
    }
  }, [])

  useEffect(() => {
    if (appliedWorkspaceNav.current) return
    const st = location.state as { url?: string } | null
    if (st?.url) {
      appliedWorkspaceNav.current = true
      setUrl(st.url)
      setActiveVideoId(extractYouTubeVideoId(st.url))
      navigate('/summarize', { replace: true, state: {} })
    }
  }, [location.state, navigate])

  useEffect(() => {
    setUrl((current) => (current === FALLBACK_VIDEO_URL || current === '' ? defaultVideoUrl : current))
    setActiveVideoId((current) => {
      const fallbackId = extractYouTubeVideoId(FALLBACK_VIDEO_URL)
      if (current === null || current === fallbackId) {
        return extractYouTubeVideoId(defaultVideoUrl)
      }
      return current
    })
  }, [defaultVideoUrl])

  async function pollJob(accepted: SummaryJobAcceptedResponse, sourceUrl: string) {
    for (let attempt = 0; attempt < 90; attempt += 1) {
      const next = await apiJson<SummaryJobStatusResponse>(accepted.status_url)
      if (!isMountedRef.current) {
        return
      }
      setJobStatus(next.status)

      if (next.status === 'completed' && next.result) {
        setSummary(next.result)
        setActiveVideoId(next.result.video_id)
        setSuggestedQuestions(
          next.result.suggested_questions?.length
            ? categorizePlainQuestionStrings(next.result.suggested_questions)
            : buildSuggestedQuestions(next.result),
        )
        incrementVideosProcessed()
        prependRecentVideo({
          videoId: next.result.video_id,
          url: sourceUrl,
          title: next.result.title || 'Untitled video',
        })
        return
      }

      if (next.status === 'failed') {
        throw new Error(next.error?.detail || 'The summarize job failed.')
      }

      await wait(1200)
    }

    throw new Error('The summary is taking longer than expected. Please try again shortly.')
  }

  async function handleSummarize() {
    setError(null)
    const trimmed = url.trim()
    const videoId = extractYouTubeVideoId(trimmed)

    if (!videoId) {
      setError('Enter a valid YouTube URL before starting a summarize job.')
      return
    }

    setBusy(true)
    setSummary(null)
    setSuggestedQuestions([])
    setJobStatus('queued')
    setJobId(null)
    setActiveVideoId(videoId)

    try {
      const accepted = await apiJson<SummaryJobAcceptedResponse>('/api/v1/summarize', {
        method: 'POST',
        body: JSON.stringify({
          url: trimmed,
          summary_type: summaryType,
          language: DEFAULT_LANGUAGE,
        }),
      })
      if (!isMountedRef.current) {
        return
      }
      setJobId(accepted.job_id)
      setJobStatus(accepted.status)
      await pollJob(accepted, trimmed)
    } catch (err) {
      if (!isMountedRef.current) {
        return
      }
      setError(err instanceof Error ? err.message : String(err))
      setJobStatus('failed')
    } finally {
      if (isMountedRef.current) {
        setBusy(false)
      }
    }
  }

  function handleSuggestedQuestion(question: string) {
    navigate('/ask-ai', { state: { url: url.trim(), question } })
  }

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
          label="Summarize"
          description="Queue a long-running summary job without blocking the request."
          url={url}
          onUrlChange={setUrl}
          onSubmit={() => void handleSummarize()}
          actionLabel="Start summarize job"
          busyLabel="Summarizing..."
          busy={busy}
        >
          <Picker
            label="Style"
            selectedKey={summaryType}
            onSelectionChange={(key) => setSummaryType(key as SummaryType)}
            isDisabled={busy}
          >
            {summaryTypeOptions.map((option) => (
              <Item key={option} textValue={option}>
                {option}
              </Item>
            ))}
          </Picker>
        </VideoUrlActionBar>

        <Flex direction="row" gap="size-150" wrap marginTop="size-200" alignItems="center">
          {jobStatus ? <StatusPill status={jobStatus} /> : null}
          {jobId ? <Badge variant="neutral">Job {jobId.slice(0, 8)}</Badge> : null}
          {demoMode ? <Badge variant="yellow">Demo mode</Badge> : null}
        </Flex>

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

      <Grid columns={{ base: '1fr', L: '1.35fr 0.95fr' }} gap="size-300" alignItems="start">
        <Flex direction="column" gap="size-300">
          <View borderRadius="medium" overflow="hidden" borderWidth="thin" borderColor="gray-300" backgroundColor="gray-900">
            <View UNSAFE_className={workspace.videoAspect16x9}>
              <VideoPlayer videoId={activeVideoId} title={summary?.title} />
            </View>
          </View>

          {sectionCard(
            <>
              <Text UNSAFE_className={workspace.sectionLabel}>OUTPUT</Text>
              <Flex direction="row" justifyContent="space-between" alignItems="start" marginTop="size-100" gap="size-150" wrap>
                <Heading level={2} margin={0}>
                  Summary panel
                </Heading>
                {jobStatus ? <StatusPill status={jobStatus} /> : null}
              </Flex>
              <View marginTop="size-200">
                <SummaryPanel
                  title={summary?.title}
                  summary={summary?.summary ?? null}
                  bullets={summary?.bullets ?? []}
                  loading={busy}
                />
              </View>
            </>,
          )}
        </Flex>

        <Flex direction="column" gap="size-300">
          {sectionCard(
            <>
              <Text UNSAFE_className={workspace.sectionLabel}>SUGGESTED FOLLOW-UPS</Text>
              <Heading level={2} marginTop="size-100">
                Ask AI next
              </Heading>
              <View marginTop="size-200">
                {busy && suggestedQuestions.length === 0 ? <SuggestedFollowUpsSkeleton /> : null}
                <SuggestedQuestions
                  items={suggestedQuestions}
                  disabled={busy}
                  onSelect={handleSuggestedQuestion}
                />
              </View>
            </>,
          )}

          {sectionCard(
            <>
              <Text UNSAFE_className={workspace.sectionLabel}>KEY MOMENTS</Text>
              <Flex direction="column" gap="size-150" marginTop="size-150">
                {summary?.key_moments?.length ? (
                  summary.key_moments.map((m) => (
                    <View
                      key={`${m.time}-${m.note}`}
                      padding="size-200"
                      borderRadius="medium"
                      borderWidth="thin"
                      borderColor="gray-200"
                      backgroundColor="gray-75"
                    >
                      <Text UNSAFE_className={workspace.keyMomentTime}>{m.time}</Text>
                      <Text UNSAFE_className={workspace.bodyLoose}>{m.note}</Text>
                    </View>
                  ))
                ) : busy ? (
                  <KeyMomentsSkeleton />
                ) : (
                  <View
                    padding="size-200"
                    borderRadius="medium"
                    borderWidth="thin"
                    borderColor="gray-300"
                    backgroundColor="gray-75"
                    UNSAFE_className={workspace.emptyStateDashed}
                  >
                    <Text>Key moments will appear here after the summary job completes.</Text>
                  </View>
                )}
              </Flex>
            </>,
          )}

          {sectionCard(
            <>
              <Text UNSAFE_className={workspace.sectionLabel}>CHAPTERS</Text>
              <Flex direction="column" gap="size-150" marginTop="size-150">
                {summary?.chapters?.length ? (
                  summary.chapters.map((c) => (
                    <View
                      key={`${c.formatted_time}-${c.title}`}
                      padding="size-200"
                      borderRadius="medium"
                      borderWidth="thin"
                      borderColor="gray-200"
                      backgroundColor="gray-75"
                    >
                      <Flex
                        direction={{ base: 'column', M: 'row' }}
                        justifyContent="space-between"
                        gap="size-100"
                        alignItems={{ M: 'center' }}
                      >
                        <Heading level={4} margin={0}>
                          {c.title}
                        </Heading>
                        <Badge variant="neutral">{c.formatted_time}</Badge>
                      </Flex>
                      <Text UNSAFE_className={workspace.bodyLoose}>{c.short_summary}</Text>
                    </View>
                  ))
                ) : busy ? (
                  <ChaptersSkeleton />
                ) : (
                  <View
                    padding="size-200"
                    borderRadius="medium"
                    borderWidth="thin"
                    borderColor="gray-300"
                    backgroundColor="gray-75"
                    UNSAFE_className={workspace.emptyStateDashed}
                  >
                    <Text>Chapters are shown when transcript segmentation is confident enough.</Text>
                  </View>
                )}
              </Flex>
            </>,
          )}
        </Flex>
      </Grid>
    </Flex>
  )
}
