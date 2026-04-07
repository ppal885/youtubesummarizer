import { Badge, Button, Flex, Grid, Heading, Text, View } from '@adobe/react-spectrum'
import { useEffect, useState } from 'react'
import { apiJson } from '../api/client'
import type { StoredSummaryListItem } from '../api/types'
import { NoVideosEmptyState } from '../components/empty-states'
import { formatDateTime, formatNumber } from '../lib/formatters'

export function HistoryPage() {
  const [items, setItems] = useState<StoredSummaryListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadHistory() {
    setLoading(true)
    setError(null)
    try {
      const data = await apiJson<StoredSummaryListItem[]>('/api/v1/summaries?limit=24')
      setItems(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadHistory()
  }, [])

  return (
    <Flex direction="column" gap="size-300">
      <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
        <Flex direction={{ base: 'column', M: 'row' }} justifyContent="space-between" alignItems={{ M: 'end' }} gap="size-200">
          <View>
            <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>HISTORY</Text>
            <Heading level={1} marginTop="size-100">
              Summary timeline
            </Heading>
            <Text UNSAFE_style={{ marginTop: 12, maxWidth: 560, lineHeight: 1.6 }}>
              Review previous outputs, language choices, and transcript sizes in one place.
            </Text>
          </View>
          <Button variant="secondary" onPress={() => void loadHistory()}>
            Refresh history
          </Button>
        </Flex>
      </View>

      {loading ? (
        <Grid columns={{ base: '1fr', XL: '1fr 1fr' }} gap="size-200">
          {Array.from({ length: 6 }).map((_, index) => (
            <View
              key={index}
              height="size-2000"
              borderRadius="medium"
              backgroundColor="gray-200"
              UNSAFE_style={{ animation: 'message-caret-pulse 1.2s ease-in-out infinite' }}
            />
          ))}
        </Grid>
      ) : null}

      {!loading && error ? (
        <View
          padding="size-200"
          borderRadius="medium"
          borderWidth="thin"
          borderColor="negative"
          backgroundColor="gray-75"
        >
          <Text UNSAFE_style={{ color: 'var(--spectrum-negative-visual-color)' }}>{error}</Text>
        </View>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <NoVideosEmptyState
          title="No history yet"
          description="Run a summarize job from the Summarize page. Saved outputs will appear here with language, transcript size, and timestamps."
        />
      ) : null}

      {!loading && !error && items.length > 0 ? (
        <Grid columns={{ base: '1fr', XL: '1fr 1fr' }} gap="size-200">
          {items.map((item) => (
            <View
              key={item.id}
              padding="size-250"
              borderRadius="medium"
              borderWidth="thin"
              borderColor="gray-200"
              backgroundColor="gray-50"
            >
              <Flex direction="row" gap="size-100" wrap>
                <Badge variant="neutral">{item.summary_type}</Badge>
                <Badge variant="info">{item.language}</Badge>
              </Flex>

              <Heading level={2} marginTop="size-200">
                {item.title}
              </Heading>
              <Text UNSAFE_style={{ marginTop: 8, lineHeight: 1.6 }}>{item.source_url}</Text>

              <Grid columns={{ base: '1fr', S: 'repeat(3, 1fr)' }} gap="size-150" marginTop="size-250">
                <View padding="size-200" borderRadius="medium" backgroundColor="gray-75">
                  <Text UNSAFE_style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em' }}>CREATED</Text>
                  <Text UNSAFE_style={{ marginTop: 8, fontWeight: 600 }}>{formatDateTime(item.created_at)}</Text>
                </View>
                <View padding="size-200" borderRadius="medium" backgroundColor="gray-75">
                  <Text UNSAFE_style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em' }}>TRANSCRIPT</Text>
                  <Text UNSAFE_style={{ marginTop: 8, fontWeight: 600 }}>{formatNumber(item.transcript_length)} chars</Text>
                </View>
                <View padding="size-200" borderRadius="medium" backgroundColor="gray-75">
                  <Text UNSAFE_style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em' }}>CHUNKS</Text>
                  <Text UNSAFE_style={{ marginTop: 8, fontWeight: 600 }}>{formatNumber(item.chunks_processed)}</Text>
                </View>
              </Grid>
            </View>
          ))}
        </Grid>
      ) : null}
    </Flex>
  )
}
