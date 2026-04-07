import { ActionButton, Flex, Heading, View } from '@adobe/react-spectrum'
import Close from '@spectrum-icons/workflow/Close'

type Props = {
  onClose?: () => void
}

export function AssistantPanelHeader({ onClose }: Props) {
  return (
    <View
      borderBottomWidth="thin"
      borderBottomColor="gray-200"
      backgroundColor="gray-50"
      paddingX="size-200"
      paddingY="size-150"
      UNSAFE_style={{ flexShrink: 0 }}
    >
      <Flex direction="row" alignItems="center" justifyContent="space-between">
        <Heading level={3} margin={0}>
          Ask about this video
        </Heading>
        <ActionButton aria-label="Close panel" onPress={onClose ?? (() => {})} isQuiet>
          <Close />
        </ActionButton>
      </Flex>
    </View>
  )
}
