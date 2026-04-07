import { Flex, View } from '@adobe/react-spectrum'

function CardRow() {
  return (
    <View padding="size-200" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-75">
      <View height="size-100" width="size-400" borderRadius="small" backgroundColor="gray-300" />
      <View marginTop="size-150" height="size-100" width="100%" borderRadius="small" backgroundColor="gray-200" />
      <View marginTop="size-100" height="size-100" width="88%" borderRadius="small" backgroundColor="gray-200" />
    </View>
  )
}

export function SuggestedFollowUpsSkeleton() {
  return (
    <div role="status" aria-label="Loading suggested questions">
      <Flex direction="column" gap="size-300" marginTop="size-200">
        <Flex direction="column" gap="size-100">
          <View height="size-100" width="size-3000" borderRadius="small" backgroundColor="gray-300" />
          <View height="size-100" width="100%" maxWidth="size-3000" borderRadius="small" backgroundColor="gray-200" />
        </Flex>
        {['Basics', 'Deep Dive', 'Practical'].map((label) => (
          <View key={label}>
            <View height="size-65" width="size-1600" borderRadius="small" backgroundColor="gray-300" />
            <Flex direction="row" gap="size-100" marginTop="size-100" wrap>
              {[1, 2].map((i) => (
                <View
                  key={`${label}-${i}`}
                  height="size-300"
                  minWidth="size-2400"
                  maxWidth="100%"
                  borderRadius="large"
                  borderWidth="thin"
                  borderColor="gray-200"
                  backgroundColor="gray-200"
                  UNSAFE_style={{ borderRadius: 9999 }}
                />
              ))}
            </Flex>
          </View>
        ))}
      </Flex>
    </div>
  )
}

export function KeyMomentsSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Loading key moments">
      <Flex direction="column" gap="size-150" marginTop="size-150">
        {Array.from({ length: rows }, (_, i) => (
          <CardRow key={i} />
        ))}
      </Flex>
    </div>
  )
}

export function ChaptersSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Loading chapters">
      <Flex direction="column" gap="size-150" marginTop="size-150">
        {Array.from({ length: rows }, (_, i) => (
          <View
            key={i}
            padding="size-200"
            borderRadius="medium"
            borderWidth="thin"
            borderColor="gray-200"
            backgroundColor="gray-75"
          >
            <Flex direction="row" justifyContent="space-between" gap="size-200" alignItems="center">
              <View height="size-150" width="70%" maxWidth="size-3000" borderRadius="small" backgroundColor="gray-300" />
              <View
                height="size-200"
                width="size-1600"
                flexShrink={0}
                borderRadius="large"
                backgroundColor="gray-200"
                UNSAFE_style={{ borderRadius: 9999 }}
              />
            </Flex>
            <View marginTop="size-150" height="size-100" width="100%" borderRadius="small" backgroundColor="gray-200" />
            <View marginTop="size-100" height="size-100" width="82%" borderRadius="small" backgroundColor="gray-200" />
          </View>
        ))}
      </Flex>
    </div>
  )
}
