import { Flex, Grid, Text, View } from '@adobe/react-spectrum'
import { useEffect, useState } from 'react'
import { apiJson } from '../api/client'
import type { FlashcardsResponse } from '../api/types'
import { VideoUrlActionBar } from '../components/VideoUrlActionBar'
import { useAppConfig } from '../context/AppConfigContext'
import { DEFAULT_LANGUAGE, FALLBACK_VIDEO_URL } from '../lib/defaults'

export function FlashcardsPage() {
  const { defaultVideoUrl } = useAppConfig()
  const [url, setUrl] = useState(defaultVideoUrl)
  const [flashcards, setFlashcards] = useState<FlashcardsResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setUrl((current) => (current === FALLBACK_VIDEO_URL || current === '' ? defaultVideoUrl : current))
  }, [defaultVideoUrl])

  async function handleGenerateFlashcards() {
    setBusy(true)
    setError(null)
    setFlashcards(null)
    try {
      const data = await apiJson<FlashcardsResponse>('/api/v1/flashcards', {
        method: 'POST',
        body: JSON.stringify({ url: url.trim(), language: DEFAULT_LANGUAGE }),
      })
      setFlashcards(data)
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
          label="Flashcards"
          description="Review concepts in a card-first layout designed for repetition."
          url={url}
          onUrlChange={setUrl}
          onSubmit={() => void handleGenerateFlashcards()}
          actionLabel="Generate flashcards"
          busyLabel="Building deck..."
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

      {flashcards?.cards?.length ? (
        <Grid columns={{ base: '1fr', M: '1fr 1fr', XL: '1fr 1fr 1fr' }} gap="size-200">
          {flashcards.cards.map((card, index) => (
            <View
              key={`${card.front}-${index}`}
              padding="size-250"
              borderRadius="medium"
              borderWidth="thin"
              borderColor="gray-200"
              backgroundColor="gray-50"
              height="100%"
            >
              <Flex direction="column" gap="size-200">
                <View padding="size-200" borderRadius="medium" backgroundColor="gray-900">
                  <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', color: '#a5f3fc' }}>
                    FRONT
                  </Text>
                  <Text UNSAFE_style={{ marginTop: 12, fontSize: 20, fontWeight: 700, color: '#fff' }}>{card.front}</Text>
                </View>
                <View padding="size-200" borderRadius="medium" backgroundColor="gray-75">
                  <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em' }}>BACK</Text>
                  <Text UNSAFE_style={{ marginTop: 12, lineHeight: 1.6 }}>{card.back}</Text>
                </View>
                {card.formatted_time ? (
                  <View padding="size-150" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
                    <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em' }}>
                      Anchor timestamp · {card.formatted_time}
                    </Text>
                  </View>
                ) : null}
              </Flex>
            </View>
          ))}
        </Grid>
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
            <Text>Generate flashcards to populate a responsive deck view here.</Text>
          </View>
        </View>
      )}
    </Flex>
  )
}
