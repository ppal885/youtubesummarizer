import { Flex, Grid, Text, View } from '@adobe/react-spectrum'
import type { UsageStats } from '../../dashboard/usageStorage'
import { formatNumber } from '../../lib/formatters'

type Props = {
  stats: UsageStats
}

export function DashboardStatsCards({ stats }: Props) {
  const items = [
    {
      label: 'Videos processed',
      value: stats.videosProcessed,
      hint: 'Successful summarizations (this browser)',
      icon: (
        <svg width={20} height={20} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.75}
            d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
          />
        </svg>
      ),
    },
    {
      label: 'Questions asked',
      value: stats.questionsAsked,
      hint: 'Copilot answers (this browser)',
      icon: (
        <svg width={20} height={20} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.75}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      ),
    },
  ]

  return (
    <Grid columns={{ base: '1fr', M: '1fr 1fr' }} gap="size-200">
      {items.map((item) => (
        <View
          key={item.label}
          padding="size-250"
          borderRadius="medium"
          borderWidth="thin"
          borderColor="gray-200"
          backgroundColor="gray-50"
        >
          <Flex justifyContent="space-between" alignItems="start" gap="size-150">
            <Flex direction="column" gap="size-75">
              <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.06em' }}>{item.label}</Text>
              <Text UNSAFE_style={{ fontSize: 28, fontWeight: 700 }}>{formatNumber(item.value)}</Text>
              <Text UNSAFE_style={{ fontSize: 12 }}>{item.hint}</Text>
            </Flex>
            <View padding="size-100" borderRadius="small" backgroundColor="gray-100" UNSAFE_style={{ color: 'var(--spectrum-gray-600)' }}>
              {item.icon}
            </View>
          </Flex>
        </View>
      ))}
    </Grid>
  )
}
