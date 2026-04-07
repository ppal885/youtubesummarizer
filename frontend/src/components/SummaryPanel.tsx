import { Flex, Heading, Text, View } from '@adobe/react-spectrum'
import { bulletLeadBold } from '../utils/bulletEmphasis'
import { SummarySkeletonLoader } from './loading'

type Props = {
  title?: string
  summary: string | null
  bullets: string[]
  loading?: boolean
  emptyHint?: string
}

export function SummaryPanel({
  title,
  summary,
  bullets,
  loading,
  emptyHint = 'Summarize a video to see an overview and key takeaways here.',
}: Props) {
  if (loading) {
    return <SummarySkeletonLoader />
  }

  if (!summary && bullets.length === 0) {
    return (
      <View
        padding="size-200"
        borderRadius="medium"
        borderWidth="thin"
        borderColor="gray-300"
        backgroundColor="gray-75"
        UNSAFE_style={{ borderStyle: 'dashed' }}
      >
        <Text>{emptyHint}</Text>
      </View>
    )
  }

  return (
    <Flex direction="column" gap="size-300">
      <View
        padding="size-200"
        borderRadius="medium"
        borderWidth="thin"
        borderColor="gray-200"
        backgroundColor="gray-50"
      >
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em' }}>SUMMARY</Text>
        {title ? (
          <Text UNSAFE_style={{ fontWeight: 600, marginTop: 8 }}>{title}</Text>
        ) : null}
        <Text UNSAFE_style={{ marginTop: title ? 8 : 12, lineHeight: 1.6 }}>{summary}</Text>
      </View>

      {bullets.length > 0 ? (
        <View>
          <Heading level={4} margin={0}>
            Key takeaways
          </Heading>
          <ul style={{ listStyle: 'none', padding: 0, margin: '12px 0 0' }}>
            {bullets.map((b, i) => (
              <li key={i} style={{ marginBottom: 12 }}>
                <Flex gap="size-100" alignItems="start">
                  <View
                    marginTop="size-65"
                    width="size-65"
                    height="size-65"
                    borderRadius="large"
                  UNSAFE_style={{ borderRadius: 9999 }}
                    backgroundColor="gray-400"
                    flexShrink={0}
                    aria-hidden
                  />
                  <Text UNSAFE_style={{ lineHeight: 1.6 }}>{bulletLeadBold(b)}</Text>
                </Flex>
              </li>
            ))}
          </ul>
        </View>
      ) : null}
    </Flex>
  )
}
