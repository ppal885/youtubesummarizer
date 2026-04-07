import { Button, Flex, Heading, Text, TextField, View } from '@adobe/react-spectrum'
import { useState } from 'react'
import { extractYouTubeVideoId } from '../../utils/youtube'

type Props = {
  onOpenWorkspace: (url: string) => void
  demoSampleUrl: string | null
  demoMode: boolean
  onFocusPasteField?: () => void
}

export function DashboardQuickActions({
  onOpenWorkspace,
  demoSampleUrl,
  demoMode,
  onFocusPasteField,
}: Props) {
  const [pasteUrl, setPasteUrl] = useState('')
  const [pasteError, setPasteError] = useState<string | null>(null)

  const tryOpen = () => {
    const t = pasteUrl.trim()
    if (!t) {
      setPasteError('Paste a YouTube link first.')
      return
    }
    if (!extractYouTubeVideoId(t)) {
      setPasteError('That does not look like a valid YouTube URL.')
      return
    }
    setPasteError(null)
    onOpenWorkspace(t)
  }

  return (
    <View
      padding="size-300"
      borderRadius="medium"
      borderWidth="thin"
      borderColor="gray-200"
      backgroundColor="gray-50"
    >
      <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.08em' }}>QUICK ACTIONS</Text>
      <Heading level={3} marginTop="size-100">
        Start a session
      </Heading>
      <Text UNSAFE_style={{ fontSize: 14, marginTop: 4 }}>Paste a link or jump into the offline demo.</Text>

      <Flex direction="column" gap="size-200" marginTop="size-300">
        <TextField
          id="dashboard-paste-yt"
          label="Paste YouTube link"
          value={pasteUrl}
          onChange={(v) => {
            setPasteUrl(v)
            setPasteError(null)
          }}
          onFocus={() => onFocusPasteField?.()}
          onKeyDown={(e) => {
            if (e.key === 'Enter') tryOpen()
          }}
          placeholder="https://www.youtube.com/watch?v=…"
        />
        {pasteError ? (
          <div role="alert">
            <Text UNSAFE_style={{ color: 'var(--spectrum-red-800)', fontSize: 12 }}>{pasteError}</Text>
          </div>
        ) : null}
        <Button variant="accent" onPress={tryOpen}>
          Open workspace
        </Button>

        {demoMode && demoSampleUrl ? (
          <Button variant="secondary" onPress={() => onOpenWorkspace(demoSampleUrl)}>
            Open offline demo video
          </Button>
        ) : null}

        <View borderTopWidth="thin" borderColor="gray-200" paddingTop="size-200">
          <Button isDisabled variant="secondary">
            Upload transcript (coming soon)
          </Button>
        </View>
      </Flex>
    </View>
  )
}
