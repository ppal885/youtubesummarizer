import { Badge, Button, Flex, Heading, ProgressBar, Text, View } from '@adobe/react-spectrum'
import type { CSSProperties } from 'react'
import { useCallback, useMemo, useState } from 'react'
import type { QuizQuestionItem, QuizResponse } from '../../api/types'

type Phase = 'quiz' | 'summary' | 'review'

type Props = {
  quiz: QuizResponse
}

const LABELS = ['A', 'B', 'C', 'D'] as const

function optionStyle(
  option: string,
  question: QuizQuestionItem,
  picked: string | null,
  revealed: boolean,
): CSSProperties {
  const isCorrect = option === question.answer
  const isPicked = option === picked
  const base: CSSProperties = {
    width: '100%',
    justifyContent: 'flex-start',
    textAlign: 'left',
    minHeight: 48,
    borderRadius: 10,
  }
  if (!revealed) {
    return { ...base, border: '1px solid var(--spectrum-gray-300)', backgroundColor: 'var(--spectrum-gray-50)' }
  }
  if (isCorrect) {
    return {
      ...base,
      border: '2px solid var(--spectrum-positive-visual-color)',
      backgroundColor: 'var(--spectrum-positive-color-100)',
      fontWeight: 600,
    }
  }
  if (isPicked && !isCorrect) {
    return {
      ...base,
      border: '2px solid var(--spectrum-negative-visual-color)',
      backgroundColor: 'var(--spectrum-negative-color-100)',
      fontWeight: 600,
    }
  }
  return { ...base, border: '1px solid var(--spectrum-gray-200)', opacity: 0.75 }
}

export function QuizSessionUI({ quiz }: Props) {
  const questions = quiz.questions
  const total = questions.length

  const [phase, setPhase] = useState<Phase>('quiz')
  const [currentIndex, setCurrentIndex] = useState(0)
  const [userAnswers, setUserAnswers] = useState<(string | null)[]>(() =>
    Array.from({ length: total }, () => null),
  )

  const current = questions[currentIndex]
  const picked = userAnswers[currentIndex]
  const revealed = picked !== null

  const { correctSoFar, answeredSoFar } = useMemo(() => {
    let correct = 0
    let answered = 0
    for (let i = 0; i < questions.length; i++) {
      const a = userAnswers[i]
      if (a !== null) {
        answered++
        if (a === questions[i].answer) correct++
      }
    }
    return { correctSoFar: correct, answeredSoFar: answered }
  }, [questions, userAnswers])

  const finalScore = useMemo(() => {
    return questions.reduce((acc, q, i) => acc + (userAnswers[i] === q.answer ? 1 : 0), 0)
  }, [questions, userAnswers])

  const selectOption = useCallback(
    (option: string) => {
      if (phase !== 'quiz') return
      setUserAnswers((prev) => {
        if (prev[currentIndex] !== null) return prev
        const next = [...prev]
        next[currentIndex] = option
        return next
      })
    },
    [phase, currentIndex],
  )

  const goNext = useCallback(() => {
    if (currentIndex >= total - 1) {
      setPhase('summary')
      return
    }
    setCurrentIndex((i) => i + 1)
  }, [currentIndex, total])

  const retryQuiz = useCallback(() => {
    setPhase('quiz')
    setCurrentIndex(0)
    setUserAnswers(Array.from({ length: total }, () => null))
  }, [total])

  const openReview = useCallback(() => setPhase('review'), [])
  const backFromReview = useCallback(() => setPhase('summary'), [])

  if (total === 0) {
    return (
      <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
        <Text UNSAFE_style={{ textAlign: 'center' }}>No questions in this quiz.</Text>
      </View>
    )
  }

  if (phase === 'review') {
    return (
      <Flex direction="column" gap="size-300">
        <Flex direction={{ base: 'column', M: 'row' }} justifyContent="space-between" alignItems={{ M: 'center' }} gap="size-200">
          <View>
            <Heading level={2}>Review answers</Heading>
            <Text UNSAFE_style={{ marginTop: 8 }}>
              {quiz.title ? `${quiz.title} · ` : null}
              You scored {finalScore} / {total}.
            </Text>
          </View>
          <Flex direction="row" gap="size-100" wrap>
            <Button variant="secondary" onPress={backFromReview}>
              Back to results
            </Button>
            <Button variant="accent" onPress={retryQuiz}>
              Retry quiz
            </Button>
          </Flex>
        </Flex>

        <Flex direction="column" gap="size-200">
          {questions.map((question, index) => {
            const userPick = userAnswers[index]
            const isRight = userPick === question.answer
            return (
              <View
                key={`${question.question}-${index}`}
                padding="size-250"
                borderRadius="medium"
                borderWidth="thin"
                borderColor="gray-200"
                backgroundColor="gray-50"
              >
                <Flex direction="row" justifyContent="space-between" alignItems="center" gap="size-100" wrap>
                  <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>
                    QUESTION {index + 1}
                  </Text>
                  <Badge variant={isRight ? 'positive' : 'negative'}>{isRight ? 'Correct' : 'Incorrect'}</Badge>
                </Flex>
                <Heading level={3} marginTop="size-100">
                  {question.question}
                </Heading>

                <GridOptions
                  question={question}
                  userPick={userPick}
                  revealed
                  onSelect={() => {}}
                  disabled
                />

                <View
                  marginTop="size-200"
                  padding="size-200"
                  borderRadius="medium"
                  borderWidth="thin"
                  borderColor="gray-200"
                  backgroundColor="gray-75"
                >
                  <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em' }}>EXPLANATION</Text>
                  <Text UNSAFE_style={{ marginTop: 8, lineHeight: 1.6 }}>{question.explanation}</Text>
                </View>
              </View>
            )
          })}
        </Flex>
      </Flex>
    )
  }

  if (phase === 'summary') {
    const pct = total > 0 ? Math.round((finalScore / total) * 100) : 0
    return (
      <View padding="size-300" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
        <Flex direction="column" alignItems="center" gap="size-200">
          <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>QUIZ COMPLETE</Text>
          <Heading level={2}>Nice work</Heading>
          <Text UNSAFE_style={{ textAlign: 'center' }}>
            You got <strong>{finalScore}</strong> out of <strong>{total}</strong> correct ({pct}%).
          </Text>
          <Flex direction={{ base: 'column', M: 'row' }} gap="size-100" marginTop="size-200">
            <Button variant="secondary" onPress={openReview}>
              Review answers
            </Button>
            <Button variant="accent" onPress={retryQuiz}>
              Retry quiz
            </Button>
          </Flex>
        </Flex>
      </View>
    )
  }

  const isCorrect = picked !== null && picked === current.answer

  return (
    <Flex direction="column" gap="size-200">
      <View
        padding="size-200"
        borderRadius="medium"
        borderWidth="thin"
        borderColor="blue-500"
        backgroundColor="static-blue-200"
      >
        <Flex direction={{ base: 'column', M: 'row' }} justifyContent="space-between" gap="size-200" alignItems={{ M: 'center' }}>
          <View>
            <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>PROGRESS</Text>
            <Text UNSAFE_style={{ marginTop: 8, fontWeight: 600 }}>
              Question {currentIndex + 1} of {total}
            </Text>
            <View marginTop="size-100" maxWidth="size-3000">
              <ProgressBar
                label="Quiz progress"
                value={currentIndex + 1}
                minValue={1}
                maxValue={total}
                UNSAFE_style={{ width: '100%' }}
              />
            </View>
          </View>
          <View>
            <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>SCORE</Text>
            <Text UNSAFE_style={{ marginTop: 8, fontSize: 22, fontWeight: 700 }}>
              {correctSoFar}
              <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--spectrum-gray-600)' }}> / {answeredSoFar}</span>
            </Text>
            <Text UNSAFE_style={{ fontSize: 12, color: 'var(--spectrum-gray-600)' }}>Correct so far</Text>
          </View>
        </Flex>
      </View>

      <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>MULTIPLE CHOICE</Text>
        <Heading level={2} marginTop="size-100">
          {current.question}
        </Heading>

        <GridOptions
          question={current}
          userPick={picked}
          revealed={revealed}
          onSelect={selectOption}
          disabled={revealed}
        />

        {revealed ? (
          <Flex direction="column" gap="size-200" marginTop="size-250">
            <View
              padding="size-200"
              borderRadius="medium"
              borderWidth="thin"
              borderColor={isCorrect ? 'positive' : 'negative'}
              backgroundColor="gray-75"
            >
              <Text UNSAFE_style={{ fontWeight: 600 }}>
                {isCorrect ? 'Correct — well done.' : 'Not quite — see the correct choice highlighted above.'}
              </Text>
            </View>
            <View padding="size-200" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-75">
              <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em' }}>EXPLANATION</Text>
              <Text UNSAFE_style={{ marginTop: 8, lineHeight: 1.6 }}>{current.explanation}</Text>
            </View>
            <Button variant="accent" onPress={goNext}>
              {currentIndex >= total - 1 ? 'View results' : 'Next question'}
            </Button>
          </Flex>
        ) : (
          <Text UNSAFE_style={{ marginTop: 16, fontSize: 12, color: 'var(--spectrum-gray-600)' }}>
            Tap an option to submit your answer.
          </Text>
        )}
      </View>
    </Flex>
  )
}

function GridOptions({
  question,
  userPick,
  revealed,
  onSelect,
  disabled,
}: {
  question: QuizQuestionItem
  userPick: string | null
  revealed: boolean
  onSelect: (o: string) => void
  disabled: boolean
}) {
  return (
    <div
      style={{
        marginTop: 20,
        display: 'grid',
        gap: 8,
        gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
      }}
      role="radiogroup"
      aria-label="Answer choices"
    >
      {question.options.map((option, optIdx) => (
        <button
          key={option}
          type="button"
          role="radio"
          aria-checked={userPick === option}
          disabled={disabled}
          onClick={() => onSelect(option)}
          style={{
            ...optionStyle(option, question, userPick, revealed),
            cursor: disabled ? 'default' : 'pointer',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 12,
            padding: '12px 14px',
          }}
        >
          <span
            style={{
              flexShrink: 0,
              width: 28,
              height: 28,
              borderRadius: 8,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 12,
              fontWeight: 700,
              background: 'var(--spectrum-gray-200)',
            }}
          >
            {LABELS[optIdx]}
          </span>
          <span style={{ textAlign: 'left', lineHeight: 1.35 }}>{option}</span>
        </button>
      ))}
    </div>
  )
}
