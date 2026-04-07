import { Flex, Grid, View } from '@adobe/react-spectrum'

function ShimmerBlock({ width = '100%', maxWidth }: { width?: string; maxWidth?: string | number }) {
  return (
    <View
      height="size-100"
      width={width}
      maxWidth={maxWidth}
      borderRadius="small"
      backgroundColor="gray-300"
      UNSAFE_style={{ animation: 'message-caret-pulse 1.2s ease-in-out infinite' }}
    />
  )
}

export function NotesLoadingShimmer() {
  return (
    <div role="status" aria-live="polite" aria-label="Generating notes">
      <Grid columns={{ base: '1fr', L: '1.15fr 0.85fr' }} gap="size-300">
        <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
          <ShimmerBlock width="size-400" />
          <View marginTop="size-200">
            <ShimmerBlock maxWidth="size-4600" />
          </View>
          <Flex direction="column" gap="size-300" marginTop="size-300">
            {[1, 2].map((i) => (
              <View
                key={i}
                padding="size-250"
                borderRadius="medium"
                borderWidth="thin"
                borderColor="gray-200"
                backgroundColor="gray-75"
              >
                <ShimmerBlock width="size-3000" />
                <Flex direction="column" gap="size-100" marginTop="size-200">
                  <ShimmerBlock />
                  <ShimmerBlock width="96%" />
                  <ShimmerBlock />
                  <ShimmerBlock width="88%" />
                  <ShimmerBlock width="92%" />
                </Flex>
              </View>
            ))}
          </Flex>
        </View>

        <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
          <ShimmerBlock width="size-2400" />
          <Flex direction="column" gap="size-150" marginTop="size-200">
            {[1, 2, 3].map((i) => (
              <View
                key={i}
                padding="size-200"
                borderRadius="medium"
                borderWidth="thin"
                borderColor="gray-200"
                backgroundColor="gray-75"
              >
                <ShimmerBlock width="size-2400" />
                <Flex direction="column" gap="size-100" marginTop="size-150">
                  <ShimmerBlock />
                  <ShimmerBlock width="85%" />
                </Flex>
              </View>
            ))}
          </Flex>
        </View>
      </Grid>
    </div>
  )
}
