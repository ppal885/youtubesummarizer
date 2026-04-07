import { ActionButton, Divider, Flex, Heading, Text, View } from '@adobe/react-spectrum'
import { useEffect, useState } from 'react'
import type { AssistantContent } from './navigation'

const XL = '(min-width: 1280px)'

type Props = {
  assistant?: AssistantContent
  open: boolean
  onClose: () => void
}

export function AssistantRail({ assistant, open, onClose }: Props) {
  const [isXl, setIsXl] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia(XL)
    const sync = () => setIsXl(mq.matches)
    sync()
    mq.addEventListener('change', sync)
    return () => mq.removeEventListener('change', sync)
  }, [])

  if (!assistant) {
    return null
  }

  const body = (
    <View padding="size-250" height="100%">
      <Flex direction="column" gap="size-200" height="100%">
        <Flex justifyContent="space-between" alignItems="start" gap="size-150">
          <Flex direction="column" gap="size-100">
            <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em' }}>{assistant.eyebrow}</Text>
            <Heading level={3} margin={0}>
              {assistant.title}
            </Heading>
          </Flex>
          {!isXl ? (
            <ActionButton isQuiet onPress={onClose} aria-label="Close assistant">
              ✕
            </ActionButton>
          ) : null}
        </Flex>

        <View padding="size-200" borderRadius="medium" backgroundColor="gray-50" borderWidth="thin" borderColor="gray-200">
          <Text>{assistant.description}</Text>
        </View>

        <Flex direction="column" gap="size-150" flex={1} minHeight={0} UNSAFE_style={{ overflowY: 'auto' }}>
          {assistant.bullets.map((bullet) => (
            <View
              key={bullet}
              padding="size-150"
              borderRadius="medium"
              backgroundColor="gray-75"
              borderWidth="thin"
              borderColor="gray-200"
            >
              <Text>{bullet}</Text>
            </View>
          ))}
        </Flex>

        <Divider size="S" />

        <View padding="size-200" borderRadius="medium" backgroundColor="gray-100">
          <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.1em' }}>OPERATOR NOTE</Text>
          <Text UNSAFE_style={{ marginTop: 8 }}>{assistant.footer}</Text>
        </View>
      </Flex>
    </View>
  )

  if (isXl) {
    return (
      <View
        width={320}
        minWidth={320}
        borderStartWidth="thin"
        borderColor="gray-200"
        backgroundColor="gray-50"
        minHeight={0}
      >
        {body}
      </View>
    )
  }

  return (
    <>
      <button
        type="button"
        aria-label="Close assistant"
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 1000,
          border: 'none',
          margin: 0,
          padding: 0,
          background: open ? 'rgba(0,0,0,0.4)' : 'transparent',
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'auto' : 'none',
          transition: 'opacity 0.2s ease',
        }}
      />
      <View
        position="fixed"
        top={0}
        right={0}
        height="100%"
        width={320}
        maxWidth="100vw"
        backgroundColor="gray-50"
        borderStartWidth="thin"
        borderColor="gray-200"
        zIndex={1001}
        UNSAFE_style={{
          transform: open ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.25s ease',
        }}
      >
        {body}
      </View>
    </>
  )
}
