import { Button, Flex, Text, TextArea, View } from '@adobe/react-spectrum'
import Send from '@spectrum-icons/workflow/Send'
import type { TextFieldRef } from '@react-types/textfield'
import { useEffect, useRef } from 'react'

const MAX_TEXTAREA_HEIGHT_PX = 200

type Props = {
  value: string
  onChange: (v: string) => void
  onSend: () => void
  disabled?: boolean
  sending?: boolean
  placeholder?: string
  id?: string
}

export function ChatComposer({
  value,
  onChange,
  onSend,
  disabled,
  sending,
  placeholder = 'Ask anything…',
  id,
}: Props) {
  const taRef = useRef<TextFieldRef<HTMLTextAreaElement>>(null)

  useEffect(() => {
    const el = taRef.current?.getInputElement()
    if (!el) return
    el.style.height = '0px'
    const next = Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)
    el.style.height = `${next}px`
  }, [value])

  const busy = disabled || sending

  return (
    <View
      padding="size-150"
      borderTopWidth="thin"
      borderTopColor="gray-200"
      backgroundColor="gray-50"
      UNSAFE_style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom, 0px))' }}
    >
      <View
        padding="size-100"
        borderRadius="medium"
        borderWidth="thin"
        borderColor="gray-200"
        backgroundColor="gray-75"
      >
        <Flex direction="row" gap="size-100" alignItems="end">
        <View flex={1} minWidth={0} width="100%">
          <TextArea
            id={id}
            ref={taRef}
            aria-label="Message"
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            isDisabled={busy}
            width="100%"
            minHeight="size-800"
            UNSAFE_style={{ resize: 'none', overflow: 'auto', maxHeight: 200 }}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              if (!busy && value.trim()) onSend()
            }
          }}
          />
        </View>
        <Button
          variant="accent"
          aria-label="Send message"
          onPress={onSend}
          isDisabled={busy || !value.trim()}
          minWidth="size-600"
          minHeight="size-600"
        >
          <Send />
        </Button>
        </Flex>
      </View>
      <Text UNSAFE_style={{ fontSize: 10, marginTop: 8, marginLeft: 4, color: 'var(--spectrum-gray-500)' }}>
        Enter to send · Shift+Enter for newline
      </Text>
    </View>
  )
}
