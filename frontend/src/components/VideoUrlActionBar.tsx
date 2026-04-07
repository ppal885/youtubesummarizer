import type { ReactNode } from 'react'
import { Button, Flex, Heading, Text, TextField, View } from '@adobe/react-spectrum'

type Props = {
  label: string
  description: string
  url: string
  onUrlChange: (value: string) => void
  onSubmit: () => void
  actionLabel: string
  busyLabel?: string
  busy?: boolean
  children?: ReactNode
}

export function VideoUrlActionBar({
  label,
  description,
  url,
  onUrlChange,
  onSubmit,
  actionLabel,
  busyLabel,
  busy = false,
  children,
}: Props) {
  return (
    <Flex direction="column" gap="size-200">
      <View>
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>{label}</Text>
        <Heading level={1} marginTop="size-50">
          {description}
        </Heading>
      </View>

      <Flex direction={{ base: 'column', M: 'row' }} gap="size-150" alignItems={{ M: 'end' }}>
        <View flex={1} minWidth={0} width="100%">
          <TextField
            label="YouTube URL"
            aria-label="YouTube URL"
            value={url}
            onChange={onUrlChange}
            placeholder="Paste a YouTube watch URL"
            type="url"
            width="100%"
          />
        </View>

        {children ? (
          <Flex direction="row" gap="size-150" wrap alignItems="end">
            {children}
          </Flex>
        ) : null}

        <Button variant="accent" onPress={onSubmit} isDisabled={busy}>
          {busy ? (busyLabel ?? actionLabel) : actionLabel}
        </Button>
      </Flex>
    </Flex>
  )
}
