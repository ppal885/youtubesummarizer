import { Flex, Grid, Heading, ProgressCircle, Text, View } from '@adobe/react-spectrum'
import type { DashboardRecentVideo } from '../../dashboard/mergeRecentVideos'
import { videoCardGradientForId } from '../../lib/dashboardGradients'
import { NoVideosEmptyState } from '../empty-states'
import { DashboardVideoCard } from './DashboardVideoCard'

type Props = {
  videos: DashboardRecentVideo[]
  loading: boolean
  onOpenVideo: (url: string, title: string) => void
  onQuickPaste: () => void
}

export function DashboardRecentSection({
  videos,
  loading,
  onOpenVideo,
  onQuickPaste,
}: Props) {
  return (
    <View
      padding="size-300"
      borderRadius="medium"
      borderWidth="thin"
      borderColor="gray-200"
      backgroundColor="gray-50"
    >
      <Flex direction="column" gap="size-100">
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em' }}>LIBRARY</Text>
        <Heading level={3} margin={0}>
          Recent videos
        </Heading>
        <Text UNSAFE_style={{ fontSize: 14 }}>Click a card to open the summarize workspace.</Text>
      </Flex>

      <View marginTop="size-300">
        {loading ? (
          <View padding="size-400">
            <Flex justifyContent="center">
              <ProgressCircle size="L" aria-label="Loading recent videos" isIndeterminate />
            </Flex>
          </View>
        ) : videos.length === 0 ? (
          <NoVideosEmptyState onPasteLink={onQuickPaste} />
        ) : (
          <Grid columns={{ base: '1fr', M: '1fr 1fr', L: '1fr 1fr 1fr' }} gap="size-200">
            {videos.map((v) => (
              <View key={v.videoId}>
                <DashboardVideoCard
                  title={v.title}
                  subtitle={new Date(v.processedAt).toLocaleString(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                  thumbnailBackground={videoCardGradientForId(v.videoId)}
                  onClick={() => onOpenVideo(v.url, v.title)}
                />
              </View>
            ))}
          </Grid>
        )}
      </View>
    </View>
  )
}
