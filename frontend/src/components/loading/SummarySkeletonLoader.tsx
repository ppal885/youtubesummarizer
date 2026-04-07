import { Flex, ProgressCircle, Text, View } from '@adobe/react-spectrum'

/**
 * Loading state mirroring SummaryPanel layout (summary block + key takeaways).
 */
export function SummarySkeletonLoader() {
  const bar = (
    <View height="size-100" borderRadius="small" backgroundColor="gray-300" width="100%" maxWidth="size-2400" />
  )
  const line = <View height="size-100" borderRadius="small" backgroundColor="gray-200" width="100%" />

  return (
    <div role="status" aria-live="polite" aria-label="Loading summary">
    <Flex direction="column" gap="size-300">
      <View padding="size-200" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
        <View marginBottom="size-150">{bar}</View>
        <View marginBottom="size-150" maxWidth="size-4600">
          {bar}
        </View>
        <Flex direction="column" gap="size-100">
          {line}
          <View maxWidth="94%">{line}</View>
          <View maxWidth="88%">{line}</View>
          {line}
          <View maxWidth="72%">{line}</View>
        </Flex>
      </View>

      <View>
        <View marginBottom="size-200" height="size-100" width="size-2000" borderRadius="small" backgroundColor="gray-300" />
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {[1, 2, 3, 4].map((i) => (
            <li key={i} style={{ marginBottom: 16 }}>
              <Flex gap="size-100" alignItems="start">
                <View
                  marginTop="size-65"
                  width="size-65"
                  height="size-65"
                  borderRadius="large"
                  backgroundColor="gray-300"
                  flexShrink={0}
                  aria-hidden
                  UNSAFE_style={{ borderRadius: 9999 }}
                />
                <Flex direction="column" gap="size-100" flex={1} minWidth={0}>
                  {line}
                  <View maxWidth="90%">{line}</View>
                </Flex>
              </Flex>
            </li>
          ))}
        </ul>
      </View>

      <Flex justifyContent="center" alignItems="center" gap="size-150">
        <ProgressCircle size="S" aria-label="Loading" isIndeterminate />
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.12em' }}>GENERATING SUMMARY…</Text>
      </Flex>
    </Flex>
    </div>
  )
}
