import { Flex, Grid, Heading, Text, View } from '@adobe/react-spectrum'
import { useEffect, useState } from 'react'
import { apiJson } from '../api/client'
import type { NotesResponse } from '../api/types'
import { NotesLoadingShimmer } from '../components/loading'
import { VideoUrlActionBar } from '../components/VideoUrlActionBar'
import { useAppConfig } from '../context/AppConfigContext'
import { DEFAULT_LANGUAGE, FALLBACK_VIDEO_URL } from '../lib/defaults'

export function NotesPage() {
  const { defaultVideoUrl } = useAppConfig()
  const [url, setUrl] = useState(defaultVideoUrl)
  const [notes, setNotes] = useState<NotesResponse | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setUrl((current) => (current === FALLBACK_VIDEO_URL || current === '' ? defaultVideoUrl : current))
  }, [defaultVideoUrl])

  async function handleGenerateNotes() {
    setBusy(true)
    setError(null)
    setNotes(null)
    try {
      const data = await apiJson<NotesResponse>('/api/v1/notes', {
        method: 'POST',
        body: JSON.stringify({ url: url.trim(), language: DEFAULT_LANGUAGE }),
      })
      setNotes(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  const errBox = error ? (
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
  ) : null

  return (
    <Flex direction="column" gap="size-300">
      <View padding="size-300" borderRadius="medium" borderWidth="thin" borderColor="blue-500" backgroundColor="static-blue-200">
        <VideoUrlActionBar
          label="Notes"
          description="Generate study-ready notes and glossary terms from the transcript."
          url={url}
          onUrlChange={setUrl}
          onSubmit={() => void handleGenerateNotes()}
          actionLabel="Generate notes"
          busyLabel="Building notes..."
          busy={busy}
        />
        {errBox}
      </View>

      {busy ? (
        <NotesLoadingShimmer />
      ) : (
        <Grid columns={{ base: '1fr', L: '1.15fr 0.85fr' }} gap="size-300" alignItems="start">
          <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
            <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>NOTES</Text>
            <Heading level={2} marginTop="size-100">
              {notes?.title ?? 'Transcript notes'}
            </Heading>

            {notes ? (
              <Flex direction="column" gap="size-300" marginTop="size-300">
                <View padding="size-250" borderRadius="medium" backgroundColor="gray-75">
                  <Text UNSAFE_style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em' }}>CONCISE NOTES</Text>
                  <Text UNSAFE_style={{ marginTop: 12, whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>{notes.concise_notes}</Text>
                </View>
                <View padding="size-250" borderRadius="medium" backgroundColor="gray-75">
                  <Text UNSAFE_style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.12em' }}>DETAILED NOTES</Text>
                  <Text UNSAFE_style={{ marginTop: 12, whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>{notes.detailed_notes}</Text>
                </View>
              </Flex>
            ) : (
              <View
                marginTop="size-300"
                padding="size-400"
                borderRadius="medium"
                borderWidth="thin"
                borderColor="gray-300"
                backgroundColor="gray-75"
                UNSAFE_style={{ borderStyle: 'dashed', textAlign: 'center' }}
              >
                <Text>Run the notes workflow to see concise and detailed write-ups here.</Text>
              </View>
            )}
          </View>

          <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
            <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>GLOSSARY</Text>
            <Flex direction="column" gap="size-150" marginTop="size-200">
              {notes?.glossary_terms?.length ? (
                notes.glossary_terms.map((term) => (
                  <View
                    key={term.term}
                    padding="size-200"
                    borderRadius="medium"
                    borderWidth="thin"
                    borderColor="gray-200"
                    backgroundColor="gray-75"
                  >
                    <Text UNSAFE_style={{ fontWeight: 600 }}>{term.term}</Text>
                    <Text UNSAFE_style={{ marginTop: 8, lineHeight: 1.6 }}>{term.definition}</Text>
                  </View>
                ))
              ) : (
                <View
                  padding="size-400"
                  borderRadius="medium"
                  borderWidth="thin"
                  borderColor="gray-300"
                  backgroundColor="gray-75"
                  UNSAFE_style={{ borderStyle: 'dashed', textAlign: 'center' }}
                >
                  <Text>Glossary terms will appear here once notes are generated.</Text>
                </View>
              )}
            </Flex>
          </View>
        </Grid>
      )}
    </Flex>
  )
}
