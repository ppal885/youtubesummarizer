import { Flex, Heading, Text, View } from '@adobe/react-spectrum'
import { forwardRef, useEffect, useId, useImperativeHandle, useRef } from 'react'
import { loadYouTubeIframeApi, type YouTubePlayerInstance } from '../lib/youtubeIframeApi'

export type VideoPlayerHandle = {
  seekTo: (seconds: number) => void
}

type Props = {
  videoId: string | null
  title?: string
}

export const VideoPlayer = forwardRef<VideoPlayerHandle, Props>(function VideoPlayer(
  { videoId, title },
  ref,
) {
  const reactId = useId().replace(/:/g, '')
  const containerId = `yt-player-${reactId}`
  const playerRef = useRef<YouTubePlayerInstance | null>(null)

  useImperativeHandle(
    ref,
    () => ({
      seekTo(seconds: number) {
        const t = Math.max(0, seconds)
        playerRef.current?.seekTo(t, true)
      },
    }),
    [],
  )

  useEffect(() => {
    if (!videoId) {
      playerRef.current?.destroy()
      playerRef.current = null
      return
    }

    let cancelled = false

    void loadYouTubeIframeApi().then(() => {
      if (cancelled || !window.YT?.Player) return

      playerRef.current?.destroy()
      playerRef.current = null

      const Player = window.YT.Player
      const player = new Player(containerId, {
        videoId,
        width: '100%',
        height: '100%',
        playerVars: {
          rel: 0,
          enablejsapi: 1,
          origin: window.location.origin,
        },
      })
      playerRef.current = player
    })

    return () => {
      cancelled = true
      playerRef.current?.destroy()
      playerRef.current = null
    }
  }, [videoId, containerId])

  if (!videoId) {
    return (
      <Flex
        direction="column"
        alignItems="center"
        justifyContent="center"
        flex={1}
        UNSAFE_style={{ minHeight: 240, background: '#000', textAlign: 'center', padding: 24 }}
      >
        <Text UNSAFE_style={{ fontSize: 18, fontWeight: 500, color: '#d4d4d8' }}>No video loaded</Text>
        <Text UNSAFE_style={{ marginTop: 8, maxWidth: 320, fontSize: 14, color: '#a1a1aa' }}>
          Paste a YouTube link above and run <span style={{ color: '#a3a3a3' }}>Summarize</span> to load the player and
          transcript insights.
        </Text>
      </Flex>
    )
  }

  return (
    <Flex direction="column" flex={1} minHeight={0} UNSAFE_style={{ background: '#000' }}>
      <View position="relative" width="100%" UNSAFE_style={{ aspectRatio: '16 / 9', background: '#000' }}>
        <div
          id={containerId}
          title={title ? `YouTube: ${title}` : 'YouTube video'}
          style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}
        />
      </View>
      {title ? (
        <View paddingX="size-200" paddingY="size-150" borderTopWidth="thin" UNSAFE_style={{ borderTopColor: '#27272a' }}>
          <Heading level={4} margin={0}>
            <span style={{ color: '#f4f4f5', fontSize: 14, fontWeight: 500, lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
              {title}
            </span>
          </Heading>
        </View>
      ) : null}
    </Flex>
  )
})
