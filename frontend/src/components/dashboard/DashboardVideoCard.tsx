import { Flex, Text, View } from '@adobe/react-spectrum'

type Props = {
  title: string
  subtitle?: string
  thumbnailBackground: string
  onClick: () => void
}

export function DashboardVideoCard({ title, subtitle, thumbnailBackground, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        display: 'flex',
        width: '100%',
        flexDirection: 'column',
        overflow: 'hidden',
        textAlign: 'left',
        cursor: 'pointer',
        border: '1px solid var(--spectrum-gray-300)',
        borderRadius: 12,
        background: 'var(--spectrum-gray-50)',
        padding: 0,
        font: 'inherit',
      }}
    >
      <View
        UNSAFE_style={{
          aspectRatio: '16 / 9',
          width: '100%',
          background: thumbnailBackground,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <View
          padding="size-100"
          borderRadius="large"
          backgroundColor="static-white"
          UNSAFE_style={{ opacity: 0.9, borderRadius: 9999 }}
        >
          <svg width={28} height={28} fill="var(--spectrum-gray-800)" viewBox="0 0 24 24" aria-hidden>
            <path d="M8 5v14l11-7z" />
          </svg>
        </View>
      </View>
      <View padding="size-200">
        <Flex direction="column" gap="size-75">
          <Text UNSAFE_style={{ fontWeight: 600, fontSize: 14, lineHeight: 1.35 }}>{title}</Text>
          {subtitle ? (
            <Text UNSAFE_style={{ fontSize: 12, opacity: 0.85 }}>{subtitle}</Text>
          ) : null}
          <Text UNSAFE_style={{ fontSize: 11, fontWeight: 600, color: 'var(--spectrum-blue-800)' }}>
            Open workspace →
          </Text>
        </Flex>
      </View>
    </button>
  )
}
