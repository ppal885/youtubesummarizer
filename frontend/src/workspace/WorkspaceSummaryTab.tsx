import { Badge, Button, Flex, Heading, Item, Picker, Text, View } from '@adobe/react-spectrum'
import type { ReactNode } from 'react'
import { useCallback, useEffect, useRef, useState } from 'react'
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
import { StatusPill } from '../components/ui/StatusPill'
import { useAppConfig } from '../context/AppConfigContext'
import { incrementVideosProcessed, prependRecentVideo } from '../dashboard/usageStorage'
import { DEFAULT_LANGUAGE } from '../lib/defaults'
import {
  buildSuggestedQuestions,
  categorizePlainQuestionStrings,
  type SuggestedQuestionItem,
} from '../utils/suggestedQuestions'

const summaryTypeOptions: SummaryType[] = ['brief', 'bullet', 'detailed', 'technical']

function wait(ms: number) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

type Props = {
  url: string
  syncKey: string
  onSuggestedPick: (question: string) => void
}

function panel(children: ReactNode) {
  return (
    <View padding="size-200" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
      {children}
    </View>
  )
}

export function WorkspaceSummaryTab({ url, syncKey, onSuggestedPick }: Props) {
  const { demoMode } = useAppConfig()
  const [summaryType, setSummaryType] = useState<SummaryType>('bullet')
  const [summary, setSummary] = useState<FinalSummary | null>(null)
  const [suggestedQuestions, setSuggestedQuestions] = useState<SuggestedQuestionItem[]>([])
  const [jobId, setJobId] = useState<string | null>(null)
  const [jobStatus, setJobStatus] = useState<SummaryJobState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isMountedRef = useRef(true)

  useEffect(() => {
    return () => {
      isMountedRef.current = false
    }
  }, [])

  useEffect(() => {
    setSummary(null)
    setSuggestedQuestions([])
    setJobStatus(null)
    setJobId(null)
    setError(null)
    setBusy(false)
  }, [syncKey])

  const pollJob = useCallback(async (accepted: SummaryJobAcceptedResponse, sourceUrl: string) => {
    for (let attempt = 0; attempt < 90; attempt += 1) {
      const next = await apiJson<SummaryJobStatusResponse>(accepted.status_url)
      if (!isMountedRef.current) return
      setJobStatus(next.status)

      if (next.status === 'completed' && next.result) {
        setSummary(next.result)
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
  }, [])

  async function handleSummarize() {
    setError(null)
    const trimmed = url.trim()
    if (!trimmed) {
      setError('Paste a valid YouTube URL first.')
      return
    }

    setBusy(true)
    setSummary(null)
    setSuggestedQuestions([])
    setJobStatus('queued')
    setJobId(null)

    try {
      const accepted = await apiJson<SummaryJobAcceptedResponse>('/api/v1/summarize', {
        method: 'POST',
        body: JSON.stringify({
          url: trimmed,
          summary_type: summaryType,
          language: DEFAULT_LANGUAGE,
        }),
      })
      if (!isMountedRef.current) return
      setJobId(accepted.job_id)
      setJobStatus(accepted.status)
      await pollJob(accepted, trimmed)
    } catch (err) {
      if (!isMountedRef.current) return
      setError(err instanceof Error ? err.message : String(err))
      setJobStatus('failed')
    } finally {
      if (isMountedRef.current) {
        setBusy(false)
      }
    }
  }

  return (
    <Flex direction="column" gap="size-200" UNSAFE_style={{ paddingBottom: 8 }}>
      <View
        padding="size-200"
        borderRadius="medium"
        borderWidth="thin"
        borderColor="blue-500"
        backgroundColor="static-blue-200"
      >
        <Flex direction={{ base: 'column', L: 'row' }} gap="size-200" alignItems={{ L: 'end' }} justifyContent="space-between">
          <Flex direction="column" gap="size-100" flex={1} minWidth={0}>
            <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>SUMMARY JOB</Text>
            <Text UNSAFE_style={{ fontSize: 14, lineHeight: 1.5 }}>
              Async summarize for this workspace URL. Output stays here while you switch tabs.
            </Text>
            <Flex direction="row" gap="size-100" wrap alignItems="center">
              <Picker
                label="Style"
                selectedKey={summaryType}
                onSelectionChange={(key) => setSummaryType(key as SummaryType)}
                isDisabled={busy}
              >
                {summaryTypeOptions.map((opt) => (
                  <Item key={opt} textValue={opt}>
                    {opt}
                  </Item>
                ))}
              </Picker>
              {jobStatus ? <StatusPill status={jobStatus} /> : null}
              {jobId ? <Badge variant="neutral">Job {jobId.slice(0, 8)}</Badge> : null}
              {demoMode ? <Badge variant="yellow">Demo</Badge> : null}
            </Flex>
          </Flex>
          <Button variant="accent" onPress={() => void handleSummarize()} isDisabled={busy || !url.trim()}>
            {busy ? 'Summarizing…' : 'Run summarize'}
          </Button>
        </Flex>
        {error ? (
          <View
            marginTop="size-200"
            padding="size-150"
            borderRadius="medium"
            borderWidth="thin"
            borderColor="negative"
            backgroundColor="gray-75"
          >
            <Text UNSAFE_style={{ color: 'var(--spectrum-negative-visual-color)', fontSize: 14 }}>{error}</Text>
          </View>
        ) : null}
      </View>

      {panel(
        <SummaryPanel
          title={summary?.title}
          summary={summary?.summary ?? null}
          bullets={summary?.bullets ?? []}
          loading={busy}
          emptyHint="Run a summarize job to see the narrative and key takeaways for this video."
        />,
      )}

      {panel(
        <>
          <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>KEY TAKEAWAYS</Text>
          {summary?.bullets?.length ? (
            <ul style={{ listStyle: 'none', padding: 0, margin: '12px 0 0' }}>
              {summary.bullets.map((b, i) => (
                <li key={i} style={{ marginBottom: 10 }}>
                  <Flex gap="size-100" alignItems="start">
                    <View
                      marginTop="size-65"
                      width="size-65"
                      height="size-65"
                      borderRadius="large"
                      backgroundColor="blue-500"
                      flexShrink={0}
                      aria-hidden
                      UNSAFE_style={{ borderRadius: 9999 }}
                    />
                    <Text UNSAFE_style={{ lineHeight: 1.6 }}>{b}</Text>
                  </Flex>
                </li>
              ))}
            </ul>
          ) : busy ? (
            <Flex direction="column" gap="size-100" marginTop="size-150">
              <View height="size-100" width="size-2400" borderRadius="small" backgroundColor="gray-300" />
              <View height="size-100" width="100%" borderRadius="small" backgroundColor="gray-200" />
              <View height="size-100" width="90%" borderRadius="small" backgroundColor="gray-200" />
            </Flex>
          ) : (
            <Text UNSAFE_style={{ marginTop: 12, fontSize: 14 }}>Bullet takeaways appear when the summary job completes.</Text>
          )}
        </>,
      )}

      {panel(
        <>
          {busy && suggestedQuestions.length === 0 ? (
            <SuggestedFollowUpsSkeleton />
          ) : (
            <SuggestedQuestions
              items={suggestedQuestions}
              disabled={busy}
              hint="Switches to the Ask AI tab with this prompt. Send when you are ready."
              onSelect={onSuggestedPick}
            />
          )}
        </>,
      )}

      {panel(
        <>
          <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>KEY MOMENTS</Text>
          <Flex direction="column" gap="size-100" marginTop="size-150">
            {summary?.key_moments?.length ? (
              summary.key_moments.map((moment) => (
                <View
                  key={`${moment.time}-${moment.note}`}
                  padding="size-150"
                  borderRadius="medium"
                  borderWidth="thin"
                  borderColor="gray-200"
                  backgroundColor="gray-75"
                >
                  <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', color: 'var(--spectrum-celery-900)' }}>
                    {moment.time}
                  </Text>
                  <Text UNSAFE_style={{ marginTop: 6, lineHeight: 1.6 }}>{moment.note}</Text>
                </View>
              ))
            ) : busy ? (
              <KeyMomentsSkeleton />
            ) : (
              <Text>No moments yet.</Text>
            )}
          </Flex>
        </>,
      )}

      {panel(
        <>
          <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>CHAPTERS</Text>
          <Flex direction="column" gap="size-100" marginTop="size-150">
            {summary?.chapters?.length ? (
              summary.chapters.map((chapter) => (
                <View
                  key={`${chapter.formatted_time}-${chapter.title}`}
                  padding="size-150"
                  borderRadius="medium"
                  borderWidth="thin"
                  borderColor="gray-200"
                  backgroundColor="gray-75"
                >
                  <Flex direction="row" justifyContent="space-between" gap="size-100" wrap alignItems="center">
                    <Heading level={4} margin={0}>
                      {chapter.title}
                    </Heading>
                    <Badge variant="neutral">{chapter.formatted_time}</Badge>
                  </Flex>
                  <Text UNSAFE_style={{ marginTop: 8, lineHeight: 1.6 }}>{chapter.short_summary}</Text>
                </View>
              ))
            ) : busy ? (
              <ChaptersSkeleton />
            ) : (
              <Text>Chapters appear when segmentation is available.</Text>
            )}
          </Flex>
        </>,
      )}
    </Flex>
  )
}
