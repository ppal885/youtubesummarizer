import {
  Badge,
  Button,
  ButtonGroup,
  Content,
  Dialog,
  DialogContainer,
  Flex,
  Heading,
  ProgressBar,
  Text,
  View,
} from '@adobe/react-spectrum'
import { useEffect, useSyncExternalStore, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  getQuotaSnapshotForSync,
  subscribeUsage,
  UPGRADE_MODAL_DISMISS_SESSION_KEY,
  type QuotaSnapshot,
} from '../../dashboard/usageStorage'

const quotaSnapshot = getQuotaSnapshotForSync

type ProgressRowProps = {
  label: string
  used: number
  limit: number
  remaining: number | null
  unlimited?: boolean
  compact?: boolean
}

function ProgressRow({ label, used, limit, remaining, unlimited, compact }: ProgressRowProps) {
  const pct = unlimited ? 0 : Math.min(100, Math.round((used / limit) * 100))
  const atCap = !unlimited && remaining === 0

  return (
    <Flex direction="column" gap={compact ? 'size-65' : 'size-100'}>
      <Flex direction="row" justifyContent="space-between" alignItems="center" gap="size-100">
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</Text>
        <Text
          UNSAFE_style={{
            fontSize: 11,
            fontWeight: 500,
            flexShrink: 0,
            fontVariantNumeric: 'tabular-nums',
            color: atCap ? 'var(--spectrum-negative-visual-color)' : 'var(--spectrum-gray-600)',
          }}
        >
          {unlimited ? (
            'Unlimited'
          ) : (
            <>
              {remaining} left · {used}/{limit}
            </>
          )}
        </Text>
      </Flex>
      <ProgressBar
        aria-label={unlimited ? `${label}, unlimited` : `${label}, ${pct} percent used`}
        value={unlimited ? 0 : pct}
        showValueLabel={!unlimited}
        formatOptions={{ style: 'percent', maximumFractionDigits: 0 }}
        UNSAFE_style={{ width: '100%' }}
      />
    </Flex>
  )
}

type UpgradeLimitModalProps = {
  open: boolean
  snapshot: QuotaSnapshot
  onClose: () => void
}

function UpgradeLimitModal({ open, snapshot, onClose }: UpgradeLimitModalProps) {
  const navigate = useNavigate()

  return (
    <DialogContainer onDismiss={onClose} isDismissable isKeyboardDismissDisabled={false}>
      {open ? (
        <Dialog>
          <Heading slot="header">Upgrade to keep going</Heading>
          <Content>
            <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', color: 'var(--spectrum-negative-visual-color)' }}>
              LIMIT REACHED
            </Text>
            <Text UNSAFE_style={{ marginTop: 12, lineHeight: 1.6 }}>
              You have hit the Free plan cap for this month
              {snapshot.videosAtLimit && snapshot.questionsAtLimit
                ? ' for both video summaries and Ask AI questions.'
                : snapshot.videosAtLimit
                  ? ' for video summaries.'
                  : ' for Ask AI questions.'}{' '}
              Pro includes unlimited usage and advanced features.
            </Text>
            <View
              marginTop="size-200"
              padding="size-200"
              borderRadius="medium"
              backgroundColor="gray-75"
            >
              <Flex direction="column" gap="size-100">
                <Flex direction="row" justifyContent="space-between">
                  <Text>Summaries this month</Text>
                  <Text UNSAFE_style={{ fontWeight: 600 }}>
                    {snapshot.videosUsed} / {snapshot.videoLimit}
                  </Text>
                </Flex>
                <Flex direction="row" justifyContent="space-between">
                  <Text>Questions this month</Text>
                  <Text UNSAFE_style={{ fontWeight: 600 }}>
                    {snapshot.questionsUsed} / {snapshot.questionLimit}
                  </Text>
                </Flex>
              </Flex>
            </View>
          </Content>
          <ButtonGroup>
            <Button variant="secondary" onPress={onClose}>
              Maybe later
            </Button>
            <Button
              variant="accent"
              onPress={() => {
                onClose()
                navigate('/pricing')
              }}
            >
              Upgrade to Pro
            </Button>
          </ButtonGroup>
        </Dialog>
      ) : null}
    </DialogContainer>
  )
}

export type UsageTrackingUIProps = {
  compact?: boolean
}

export function UsageTrackingUI({ compact }: UsageTrackingUIProps) {
  const snapshot = useSyncExternalStore(subscribeUsage, quotaSnapshot, quotaSnapshot)
  const [modalOpen, setModalOpen] = useState(false)

  useEffect(() => {
    if (snapshot.plan !== 'free' || !snapshot.anyAtLimit) {
      setModalOpen(false)
      return
    }
    if (sessionStorage.getItem(UPGRADE_MODAL_DISMISS_SESSION_KEY) === '1') return
    setModalOpen(true)
  }, [snapshot.plan, snapshot.anyAtLimit, snapshot.videosAtLimit, snapshot.questionsAtLimit])

  const dismissModal = () => {
    sessionStorage.setItem(UPGRADE_MODAL_DISMISS_SESSION_KEY, '1')
    setModalOpen(false)
  }

  const isPro = snapshot.plan === 'pro'

  return (
    <>
      <View
        padding={compact ? 'size-150' : 'size-250'}
        borderRadius="medium"
        borderWidth="thin"
        borderColor="gray-200"
        backgroundColor="gray-75"
        width="100%"
        minWidth={compact ? '10rem' : undefined}
        maxWidth={compact ? '14rem' : 'size-6000'}
      >
        <Flex direction="column" gap={compact ? 'size-100' : 'size-200'}>
          <Flex direction="row" justifyContent="space-between" alignItems="center" gap="size-100">
            <Text UNSAFE_style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.12em' }}>
              {isPro ? 'USAGE (PRO)' : 'THIS MONTH'}
            </Text>
            {isPro ? (
              <Badge variant="positive" UNSAFE_style={{ fontSize: 10 }}>
                Pro
              </Badge>
            ) : null}
          </Flex>
          <ProgressRow
            label="Videos"
            used={snapshot.videosUsed}
            limit={snapshot.videoLimit}
            remaining={snapshot.videosRemaining}
            unlimited={isPro}
            compact={compact}
          />
          <ProgressRow
            label="Questions"
            used={snapshot.questionsUsed}
            limit={snapshot.questionLimit}
            remaining={snapshot.questionsRemaining}
            unlimited={isPro}
            compact={compact}
          />
          {!isPro && (snapshot.videosAtLimit || snapshot.questionsAtLimit) ? (
            <Button variant="accent" width="100%" onPress={() => setModalOpen(true)}>
              Upgrade to Pro
            </Button>
          ) : null}
        </Flex>
      </View>

      <UpgradeLimitModal
        open={modalOpen && snapshot.plan === 'free' && snapshot.anyAtLimit}
        snapshot={snapshot}
        onClose={dismissModal}
      />
    </>
  )
}
