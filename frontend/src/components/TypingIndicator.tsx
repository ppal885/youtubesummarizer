import { Flex, Text, View } from '@adobe/react-spectrum'

type Props = {
  label?: string
}

export function TypingIndicator({ label = 'Thinking…' }: Props) {
  return (
    <div role="status" aria-live="polite" aria-label={label}>
    <View
      padding="size-200"
      borderRadius="medium"
      borderWidth="thin"
      borderColor="gray-200"
      backgroundColor="gray-75"
      maxWidth="size-4600"
    >
      <Flex direction="row" gap="size-200" alignItems="center">
        <Flex direction="row" gap="size-65" aria-hidden>
          <span
            className="typing-dot"
            style={{ width: 8, height: 8, borderRadius: 9999, backgroundColor: 'var(--spectrum-gray-600)' }}
          />
          <span
            className="typing-dot typing-dot-delay-1"
            style={{ width: 8, height: 8, borderRadius: 9999, backgroundColor: 'var(--spectrum-gray-600)' }}
          />
          <span
            className="typing-dot typing-dot-delay-2"
            style={{ width: 8, height: 8, borderRadius: 9999, backgroundColor: 'var(--spectrum-gray-600)' }}
          />
        </Flex>
        <Text UNSAFE_style={{ fontSize: 12, fontWeight: 500 }}>{label}</Text>
      </Flex>
    </View>
    </div>
  )
}
