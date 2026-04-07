import { Grid, Heading, Text, View } from '@adobe/react-spectrum'
import { SUGGESTED_VIDEOS } from '../../dashboard/suggestedVideos'
import { DashboardVideoCard } from './DashboardVideoCard'

type Props = {
  onOpenVideo: (url: string, title: string) => void
}

export function DashboardSuggestedSection({ onOpenVideo }: Props) {
  return (
    <View
      padding="size-300"
      borderRadius="medium"
      borderWidth="thin"
      borderColor="gray-200"
      backgroundColor="gray-50"
    >
      <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em' }}>DISCOVER</Text>
      <Heading level={3} marginTop="size-100">
        Suggested videos
      </Heading>
      <Text UNSAFE_style={{ fontSize: 14, marginTop: 4 }}>Hand-picked links to stress-test the copilot.</Text>

      <Grid columns={{ base: '1fr', M: '1fr 1fr', L: '1fr 1fr 1fr' }} gap="size-200" marginTop="size-300">
        {SUGGESTED_VIDEOS.map((v) => (
          <View key={v.id}>
            <DashboardVideoCard
              title={v.title}
              subtitle={v.description}
              thumbnailBackground={v.thumbnailBackground}
              onClick={() => onOpenVideo(v.url, v.title)}
            />
          </View>
        ))}
      </Grid>
    </View>
  )
}
