import { Button, ButtonGroup, Flex, Heading, Text, View } from '@adobe/react-spectrum'
import type { ReactNode } from 'react'

export type SaaSEmptyStateAction = {
  label: string
  onClick: () => void
}

type Props = {
  title: string
  description: string
  illustration?: ReactNode
  primaryAction?: SaaSEmptyStateAction
  secondaryAction?: SaaSEmptyStateAction
}

export function SaaSEmptyState({
  title,
  description,
  illustration,
  primaryAction,
  secondaryAction,
}: Props) {
  return (
    <View
      padding="size-400"
      borderRadius="medium"
      borderWidth="thin"
      borderColor="gray-300"
      backgroundColor="gray-75"
      UNSAFE_style={{ borderStyle: 'dashed' }}
    >
      <Flex direction="column" alignItems="center" gap="size-200">
        {illustration ? (
          <View UNSAFE_style={{ maxWidth: 220, width: '100%', color: 'var(--spectrum-gray-600)' }}>
            {illustration}
          </View>
        ) : null}
        <Heading level={3} margin={0}>
          {title}
        </Heading>
        <Text UNSAFE_style={{ textAlign: 'center', maxWidth: 480 }}>{description}</Text>
        {(primaryAction || secondaryAction) && (
          <ButtonGroup>
            {primaryAction ? (
              <Button variant="accent" onPress={primaryAction.onClick}>
                {primaryAction.label}
              </Button>
            ) : null}
            {secondaryAction ? (
              <Button variant="secondary" onPress={secondaryAction.onClick}>
                {secondaryAction.label}
              </Button>
            ) : null}
          </ButtonGroup>
        )}
      </Flex>
    </View>
  )
}
