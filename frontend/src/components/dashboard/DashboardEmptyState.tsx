import { Flex, Heading, Text, View } from '@adobe/react-spectrum'
import type { ReactNode } from 'react'

type Props = {
  icon: ReactNode
  title: string
  description: string
  action?: ReactNode
}

export function DashboardEmptyState({ icon, title, description, action }: Props) {
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
        <View padding="size-150" borderRadius="medium" backgroundColor="gray-50">
          {icon}
        </View>
        <Heading level={4} margin={0}>
          {title}
        </Heading>
        <Text UNSAFE_style={{ textAlign: 'center', maxWidth: 360 }}>{description}</Text>
        {action ? <View>{action}</View> : null}
      </Flex>
    </View>
  )
}
