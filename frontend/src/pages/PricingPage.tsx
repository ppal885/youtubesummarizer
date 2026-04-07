import { Button, Flex, Grid, Heading, Text, View } from '@adobe/react-spectrum'
import { setBillingPlan } from '../dashboard/usageStorage'

type PlanFeature = {
  label: string
  free: string | boolean
  pro: string | boolean
}

const COMPARISON: PlanFeature[] = [
  { label: 'Video summaries', free: '5 per month', pro: 'Unlimited' },
  { label: 'Ask AI (grounded Q&A)', free: '20 questions / month', pro: 'Unlimited' },
  { label: 'Transcript length', free: 'Up to ~2 hrs / video', pro: 'Extended + priority queue' },
  { label: 'Learning tools (notes, quiz, cards)', free: 'Basic exports', pro: 'Full bundles + Markdown' },
  { label: 'RAG & context compression', free: 'Standard retrieval', pro: 'Advanced compression & wider pool' },
  { label: 'Models', free: 'Shared capacity', pro: 'Priority routing & latest models' },
  { label: 'Support', free: 'Community', pro: 'Email support (business hours)' },
  { label: 'API access', free: false, pro: true },
]

function CellValue({ value }: { value: string | boolean }) {
  if (value === true) {
    return (
      <View
        width="size-300"
        height="size-300"
        borderRadius="large"
        backgroundColor="positive"
        UNSAFE_style={{ borderRadius: 9999, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
      >
        <Text UNSAFE_style={{ color: 'white', fontSize: 12 }}>✓</Text>
      </View>
    )
  }
  if (value === false) {
    return (
      <View
        width="size-300"
        height="size-300"
        borderRadius="large"
        backgroundColor="gray-200"
        UNSAFE_style={{ borderRadius: 9999, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
      >
        <Text UNSAFE_style={{ fontSize: 12, color: 'var(--spectrum-gray-500)' }}>×</Text>
      </View>
    )
  }
  return <Text UNSAFE_style={{ fontWeight: 500 }}>{value}</Text>
}

export function PricingPage() {
  return (
    <Flex direction="column" gap="size-400">
      <View padding="size-300" borderRadius="medium" borderWidth="thin" borderColor="blue-500" backgroundColor="static-blue-200">
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>PRICING</Text>
        <Heading level={1} marginTop="size-100">
          Simple plans for individuals and power users
        </Heading>
        <Text UNSAFE_style={{ marginTop: 16, maxWidth: 560, lineHeight: 1.7 }}>
          Start free with generous limits, then upgrade when you need unlimited usage and advanced copilot features. No hidden
          fees—just clear limits you can grow past.
        </Text>
      </View>

      <Grid columns={{ base: '1fr', L: '1fr 1fr' }} gap="size-300" alignItems="stretch">
        <View padding="size-300" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
          <Flex direction="column" height="100%">
            <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em' }}>FREE</Text>
            <Heading level={2} marginTop="size-150">
              $0<Text UNSAFE_style={{ fontSize: 18, fontWeight: 500, color: 'var(--spectrum-gray-600)' }}> / month</Text>
            </Heading>
            <Text UNSAFE_style={{ marginTop: 12, lineHeight: 1.6 }}>
              Explore the full product with capped usage—perfect for occasional videos and trying Ask AI.
            </Text>
            <ul style={{ listStyle: 'none', padding: 0, margin: '20px 0 0', flex: 1 }}>
              <li style={{ marginBottom: 12 }}>Limited summaries and Q&A each month</li>
              <li style={{ marginBottom: 12 }}>Dashboard, history, and all core routes</li>
              <li style={{ marginBottom: 12 }}>Standard transcript retrieval & grounding</li>
            </ul>
            <Button variant="secondary" isDisabled marginTop="size-300">
              Current plan
            </Button>
          </Flex>
        </View>

        <View
          padding="size-25"
          borderRadius="medium"
          borderWidth="thick"
          borderColor="blue-500"
          backgroundColor="static-blue-200"
          position="relative"
        >
          <View
            position="absolute"
            top="size-200"
            right="size-200"
            paddingX="size-150"
            paddingY="size-65"
            borderRadius="large"
            backgroundColor="blue-600"
            UNSAFE_style={{ borderRadius: 9999 }}
          >
            <Text UNSAFE_style={{ color: 'white', fontSize: 11, fontWeight: 700 }}>POPULAR</Text>
          </View>
          <View padding="size-300" borderRadius="medium" backgroundColor="gray-50" height="100%">
            <Flex direction="column" height="100%">
              <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.12em', color: 'var(--spectrum-blue-900)' }}>
                PRO
              </Text>
              <Heading level={2} marginTop="size-150">
                $19<Text UNSAFE_style={{ fontSize: 18, fontWeight: 500, color: 'var(--spectrum-gray-600)' }}> / month</Text>
              </Heading>
              <Text UNSAFE_style={{ fontSize: 12, color: 'var(--spectrum-gray-600)' }}>Billed monthly. Team seats coming later.</Text>
              <Text UNSAFE_style={{ marginTop: 16, lineHeight: 1.6 }}>
                Unlimited usage, wider retrieval pool, smarter context compression, and priority throughput for serious learners
                and creators.
              </Text>
              <ul style={{ listStyle: 'none', padding: 0, margin: '20px 0 0', flex: 1 }}>
                <li style={{ marginBottom: 12 }}>
                  <strong>Unlimited</strong> summaries & grounded Q&A
                </li>
                <li style={{ marginBottom: 12 }}>Advanced RAG: wide retrieval + LLM/heuristic context compression</li>
                <li style={{ marginBottom: 12 }}>Priority jobs, richer exports, and API access (roadmap)</li>
              </ul>
              <Button variant="accent" marginTop="size-300" onPress={() => setBillingPlan('pro')}>
                Upgrade to Pro
              </Button>
              <Text UNSAFE_style={{ marginTop: 12, textAlign: 'center', fontSize: 11, color: 'var(--spectrum-gray-600)' }}>
                Secure checkout will connect here (e.g. Stripe Customer Portal).
              </Text>
            </Flex>
          </View>
        </View>
      </Grid>

      <View padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>FEATURE COMPARISON</Text>
        <Heading level={2} marginTop="size-100">
          Free vs Pro
        </Heading>
        <Text UNSAFE_style={{ marginTop: 8, maxWidth: 560, lineHeight: 1.6 }}>
          Same app surface—Pro removes caps and unlocks deeper retrieval and throughput.
        </Text>

        <View marginTop="size-300" overflow="auto" borderRadius="medium" borderWidth="thin" borderColor="gray-200">
          <table style={{ width: '100%', minWidth: 520, borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--spectrum-gray-200)', background: 'var(--spectrum-gray-75)' }}>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Feature</th>
                <th style={{ padding: '14px 16px', fontWeight: 600 }}>Free</th>
                <th style={{ padding: '14px 16px', fontWeight: 600, background: 'var(--spectrum-blue-100)' }}>Pro</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON.map((row) => (
                <tr key={row.label} style={{ borderBottom: '1px solid var(--spectrum-gray-100)' }}>
                  <th scope="row" style={{ padding: '14px 16px', fontWeight: 500 }}>
                    {row.label}
                  </th>
                  <td style={{ padding: '14px 16px' }}>
                    <CellValue value={row.free} />
                  </td>
                  <td style={{ padding: '14px 16px', background: 'var(--spectrum-blue-50)' }}>
                    <CellValue value={row.pro} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </View>

      </View>
    </Flex>
  )
}
