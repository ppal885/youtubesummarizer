import { Button, Flex, Grid, Heading, Text, View } from '@adobe/react-spectrum'
import type { ReactNode } from 'react'
import { useState } from 'react'
import { apiBase } from '../api/client'
import { ThemeToggle } from '../components/ThemeToggle'
import { useAppConfig } from '../context/AppConfigContext'

function DefRow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <View padding="size-200" borderRadius="medium" backgroundColor="gray-75">
      <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em' }}>{label}</Text>
      <View marginTop="size-100">{children}</View>
    </View>
  )
}

export function SettingsPage() {
  const { appName, appVersion, config, demoMode, error } = useAppConfig()
  const [compactMode, setCompactMode] = useState(false)
  const [assistantHints, setAssistantHints] = useState(true)

  return (
    <Flex direction="column" gap="size-300">
      <View padding="size-300" borderRadius="medium" borderWidth="thin" borderColor="blue-500" backgroundColor="static-blue-200">
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>SETTINGS</Text>
        <Heading level={1} marginTop="size-100">
          Configure the workspace shell
        </Heading>
        <Text UNSAFE_style={{ marginTop: 12, maxWidth: 720, lineHeight: 1.6 }}>
          This page surfaces backend configuration alongside product-level display preferences so the UI feels like a complete
          SaaS application, not just a feature demo.
        </Text>
      </View>

      {error ? (
        <View
          padding="size-200"
          borderRadius="medium"
          borderWidth="thin"
          borderColor="yellow-400"
          backgroundColor="gray-75"
        >
          <Text>
            Configuration could not be loaded from the API. The workspace is showing sensible defaults instead.
          </Text>
        </View>
      ) : null}

      <Grid columns={{ base: '1fr', XL: '1fr 1fr' }} gap="size-300" alignItems="start">
        <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
          <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>APPLICATION</Text>
          <Flex direction="column" gap="size-200" marginTop="size-250">
            <DefRow label="NAME">
              <Text UNSAFE_style={{ fontWeight: 600 }}>{appName}</Text>
            </DefRow>
            <DefRow label="VERSION">
              <Text UNSAFE_style={{ fontWeight: 600 }}>{appVersion}</Text>
            </DefRow>
            <DefRow label="API BASE">
              <Text UNSAFE_style={{ fontWeight: 600, wordBreak: 'break-all' }}>{apiBase() || 'Vite proxy / default origin'}</Text>
            </DefRow>
            <DefRow label="MODE">
              <Text UNSAFE_style={{ fontWeight: 600 }}>{demoMode ? 'Demo mode' : 'Live mode'}</Text>
            </DefRow>
          </Flex>
        </View>

        <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
          <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>MODEL CONFIGURATION</Text>
          <Flex direction="column" gap="size-200" marginTop="size-250">
            <DefRow label="PROVIDER">
              <Text UNSAFE_style={{ fontWeight: 600 }}>{config?.llm.provider ?? 'mock'}</Text>
            </DefRow>
            <DefRow label="MODEL">
              <Text UNSAFE_style={{ fontWeight: 600 }}>{config?.llm.model ?? 'gpt-4o-mini'}</Text>
            </DefRow>
            <DefRow label="CONFIGURED">
              <Text UNSAFE_style={{ fontWeight: 600 }}>{config?.llm.configured ? 'Ready' : 'Missing credentials'}</Text>
            </DefRow>
            <DefRow label="JSON MODE">
              <Text UNSAFE_style={{ fontWeight: 600 }}>{config?.llm.json_response_format ? 'Enabled' : 'Disabled'}</Text>
            </DefRow>
          </Flex>
        </View>
      </Grid>

      <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>PERSONAL PREFERENCES</Text>

        <View
          marginTop="size-250"
          padding="size-250"
          borderRadius="medium"
          borderWidth="thin"
          borderColor="gray-200"
          backgroundColor="gray-75"
        >
          <Flex direction={{ base: 'column', M: 'row' }} justifyContent="space-between" alignItems={{ M: 'center' }} gap="size-200">
            <View>
              <Text UNSAFE_style={{ fontWeight: 600 }}>Appearance</Text>
              <Text UNSAFE_style={{ marginTop: 8, fontSize: 14 }}>Light or dark interface. Preference is saved on this device.</Text>
            </View>
            <ThemeToggle />
          </Flex>
        </View>

        <Grid columns={{ base: '1fr', M: '1fr 1fr' }} gap="size-200" marginTop="size-200">
          <Button
            variant="secondary"
            onPress={() => setCompactMode((v) => !v)}
            UNSAFE_style={{ height: 'auto', minHeight: 100, alignItems: 'flex-start', padding: 20 }}
          >
            <Flex direction="column" alignItems="start" gap="size-100">
              <Text UNSAFE_style={{ fontWeight: 600 }}>Compact content density</Text>
              <Text UNSAFE_style={{ fontSize: 14, textAlign: 'left' }}>
                {compactMode ? 'Enabled for tighter cards and shorter surfaces.' : 'Disabled for roomy SaaS spacing.'}
              </Text>
            </Flex>
          </Button>
          <Button
            variant="secondary"
            onPress={() => setAssistantHints((v) => !v)}
            UNSAFE_style={{ height: 'auto', minHeight: 100, alignItems: 'flex-start', padding: 20 }}
          >
            <Flex direction="column" alignItems="start" gap="size-100">
              <Text UNSAFE_style={{ fontWeight: 600 }}>Assistant rail hints</Text>
              <Text UNSAFE_style={{ fontSize: 14, textAlign: 'left' }}>
                {assistantHints ? 'Route-specific guidance is surfaced in the right rail.' : 'Right-rail hints are minimized.'}
              </Text>
            </Flex>
          </Button>
        </Grid>
      </View>
    </Flex>
  )
}
