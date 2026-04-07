/** Load YouTube IFrame API once; resolves when `window.YT.Player` is available. */

declare global {
  interface Window {
    YT?: { Player: YouTubePlayerConstructor }
    onYouTubeIframeAPIReady?: () => void
  }
}

export type YouTubePlayerInstance = {
  seekTo: (seconds: number, allowSeekAhead?: boolean) => void
  destroy: () => void
}

type YouTubePlayerConstructor = new (
  containerId: string,
  options: {
    videoId: string
    width?: string | number
    height?: string | number
    playerVars?: Record<string, string | number>
    events?: { onReady?: (e: { target: YouTubePlayerInstance }) => void }
  },
) => YouTubePlayerInstance

let iframeApiPromise: Promise<void> | null = null

export function loadYouTubeIframeApi(): Promise<void> {
  if (typeof window === 'undefined') return Promise.resolve()
  if (window.YT?.Player) return Promise.resolve()

  if (!iframeApiPromise) {
    iframeApiPromise = new Promise<void>((resolve) => {
      const previous = window.onYouTubeIframeAPIReady
      window.onYouTubeIframeAPIReady = () => {
        previous?.()
        resolve()
      }

      const existing = document.querySelector<HTMLScriptElement>(
        'script[src="https://www.youtube.com/iframe_api"]',
      )
      if (!existing) {
        const tag = document.createElement('script')
        tag.src = 'https://www.youtube.com/iframe_api'
        const firstScript = document.getElementsByTagName('script')[0]
        firstScript.parentNode?.insertBefore(tag, firstScript)
      }
    })
  }

  return iframeApiPromise
}
