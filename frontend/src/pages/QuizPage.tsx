import { Flex, Text, View } from '@adobe/react-spectrum'
import { useEffect, useState } from 'react'
import { apiJson } from '../api/client'
import type { QuizResponse } from '../api/types'
import { VideoUrlActionBar } from '../components/VideoUrlActionBar'
import { QuizSessionUI } from '../components/quiz/QuizSessionUI'
import { useAppConfig } from '../context/AppConfigContext'
import { DEFAULT_LANGUAGE, FALLBACK_VIDEO_URL } from '../lib/defaults'

export function QuizPage() {
  const { defaultVideoUrl } = useAppConfig()
  const [url, setUrl] = useState(defaultVideoUrl)
  const [quiz, setQuiz] = useState<QuizResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setUrl((current) => (current === FALLBACK_VIDEO_URL || current === '' ? defaultVideoUrl : current))
  }, [defaultVideoUrl])

  async function handleGenerateQuiz() {
    setBusy(true)
    setError(null)
    setQuiz(null)
    try {
      const data = await apiJson<QuizResponse>('/api/v1/quiz', {
        method: 'POST',
        body: JSON.stringify({ url: url.trim(), language: DEFAULT_LANGUAGE }),
      })
      setQuiz(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Flex direction="column" gap="size-300">
      <View padding="size-300" borderRadius="medium" borderWidth="thin" borderColor="blue-500" backgroundColor="static-blue-200">
        <VideoUrlActionBar
          label="Quiz"
          description="Turn transcript content into multiple-choice study questions."
          url={url}
          onUrlChange={setUrl}
          onSubmit={() => void handleGenerateQuiz()}
          actionLabel="Generate quiz"
          busyLabel="Building quiz..."
          busy={busy}
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
            <Text UNSAFE_style={{ color: 'var(--spectrum-negative-visual-color)' }}>{error}</Text>
          </View>
        ) : null}
      </View>

      {quiz?.questions?.length ? (
        <QuizSessionUI
          key={quiz.questions.map((q) => q.question).join('\u0001')}
          quiz={quiz}
        />
      ) : (
        <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
          <View
            padding="size-400"
            borderRadius="medium"
            borderWidth="thin"
            borderColor="gray-300"
            backgroundColor="gray-75"
            UNSAFE_style={{ borderStyle: 'dashed', textAlign: 'center' }}
          >
            <Text>
              Generate a quiz to practice with multiple-choice questions, instant feedback, and a score at the end.
            </Text>
          </View>
        </View>
      )}
    </Flex>
  )
}
