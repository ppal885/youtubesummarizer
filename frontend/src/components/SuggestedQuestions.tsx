import { Button, Flex, Text, View } from '@adobe/react-spectrum'
import { useMemo } from 'react'
import type { SuggestedQuestionCategory, SuggestedQuestionItem } from '../utils/suggestedQuestions'

const CATEGORY_ORDER: SuggestedQuestionCategory[] = ['basics', 'deep_dive', 'practical']

const CATEGORY_LABELS: Record<SuggestedQuestionCategory, string> = {
  basics: 'Basics',
  deep_dive: 'Deep Dive',
  practical: 'Practical',
}

type Props = {
  items: SuggestedQuestionItem[]
  disabled?: boolean
  onSelect: (question: string) => void
  instantSend?: boolean
  hint?: string
}

export function SuggestedQuestions({ items, disabled, onSelect, instantSend, hint }: Props) {
  const grouped = useMemo(() => {
    const map: Record<SuggestedQuestionCategory, SuggestedQuestionItem[]> = {
      basics: [],
      deep_dive: [],
      practical: [],
    }
    for (const item of items) {
      map[item.category].push(item)
    }
    return map
  }, [items])

  if (items.length === 0) return null

  return (
    <Flex direction="column" gap="size-300">
      <View>
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>SUGGESTED QUESTIONS</Text>
        <Text UNSAFE_style={{ fontSize: 12, marginTop: 6, lineHeight: 1.5 }}>
          {hint ??
            (instantSend
              ? 'Tap a chip to fill the composer and send right away.'
              : 'Opens Ask AI with this video and your chosen prompt.')}
        </Text>
      </View>

      <Flex direction="column" gap="size-300">
        {CATEGORY_ORDER.map((category) => {
          const list = grouped[category]
          if (list.length === 0) return null
          return (
            <View key={category}>
              <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em' }}>
                {CATEGORY_LABELS[category]}
              </Text>
              <Flex direction="row" gap="size-100" marginTop="size-100" wrap>
                {list.map((item) => (
                  <Button
                    key={`${category}-${item.text}`}
                    variant="secondary"
                    isQuiet
                    isDisabled={disabled}
                    onPress={() => onSelect(item.text)}
                    UNSAFE_style={{ maxWidth: '100%', textAlign: 'left', borderRadius: 9999, height: 'auto', minHeight: 36 }}
                  >
                    <span style={{ display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                      {item.text}
                    </span>
                  </Button>
                ))}
              </Flex>
            </View>
          )
        })}
      </Flex>
    </Flex>
  )
}
