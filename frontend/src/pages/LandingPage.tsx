import { Button, Flex, Grid, Heading, Text, TextField, View } from '@adobe/react-spectrum'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ProductIcon } from '../components/brand/ProductIcon'
import { ThemeToggle } from '../components/ThemeToggle'
import { extractYouTubeVideoId } from '../utils/youtube'
import styles from './landing/LandingPage.module.css'

function scrollToSection(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function LandingNav() {
  return (
    <View
      position="sticky"
      top={0}
      zIndex={10}
      backgroundColor="gray-50"
      borderBottomWidth="thin"
      borderBottomColor="gray-200"
      UNSAFE_className={styles.stickyNav}
    >
      <Flex direction="row" alignItems="center" justifyContent="space-between" gap="size-200" UNSAFE_className={styles.navInner}>
        <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
          <Flex direction="row" alignItems="center" gap="size-100">
            <ProductIcon size={36} variant="full" title="YouTube Copilot" />
            <Text UNSAFE_style={{ fontWeight: 600 }}>YouTube Copilot</Text>
          </Flex>
        </Link>
        <nav className={styles.navLinks} aria-label="Page sections">
          <Flex direction="row" gap="size-300" alignItems="center">
            <button type="button" className={styles.navAnchor} onClick={() => scrollToSection('demo')}>
              Product
            </button>
            <button type="button" className={styles.navAnchor} onClick={() => scrollToSection('features')}>
              Features
            </button>
            <button type="button" className={styles.navAnchor} onClick={() => scrollToSection('pricing')}>
              Pricing
            </button>
          </Flex>
        </nav>
        <Flex direction="row" gap="size-150" alignItems="center">
          <ThemeToggle />
          <Link to="/dashboard" style={{ textDecoration: 'none' }} className={styles.navWorkspace}>
            <Button variant="secondary">Workspace</Button>
          </Link>
          <Link to="/summarize" style={{ textDecoration: 'none' }}>
            <Button variant="accent">Start free</Button>
          </Link>
        </Flex>
      </Flex>
    </View>
  )
}

function HeroSection({
  url,
  setUrl,
  error,
  onSubmit,
}: {
  url: string
  setUrl: (v: string) => void
  error: string | null
  onSubmit: (e: FormEvent) => void
}) {
  return (
    <section>
      <View
        backgroundColor="gray-50"
        paddingTop="size-300"
        paddingBottom="size-600"
        borderBottomWidth="thin"
        borderBottomColor="gray-200"
      >
        <View UNSAFE_className={`${styles.pageGutter} ${styles.max768} ${styles.textCenter}`}>
        <Text UNSAFE_className={styles.heroEyebrow}>AI FOR LONG-FORM VIDEO</Text>
        <Heading level={1} marginTop="size-200">
          Turn YouTube videos into notes, quizzes, and insights
        </Heading>
        <Text UNSAFE_className={`${styles.heroSub} ${styles.max520}`}>
          Paste a link. Get a grounded summary, study notes, and Q&amp;A backed by the transcript—so you learn faster without
          rewatching.
        </Text>

        <form onSubmit={onSubmit} aria-label="Start with a YouTube URL" className={`${styles.heroForm} ${styles.max520}`}>
          <Flex direction={{ base: 'column', M: 'row' }} gap="size-150" alignItems={{ M: 'end' }}>
            <TextField
              label="YouTube URL"
              aria-label="YouTube URL"
              id="landing-youtube-url"
              type="url"
              name="url"
              inputMode="url"
              autoComplete="url"
              placeholder="https://www.youtube.com/watch?v=…"
              value={url}
              onChange={setUrl}
              width="100%"
              flex={1}
            />
            <Button type="submit" variant="accent">
              Summarize this video
            </Button>
          </Flex>
          {error ? (
            <div role="alert" style={{ marginTop: 12 }}>
              <Text UNSAFE_style={{ color: 'var(--spectrum-negative-visual-color)', fontWeight: 500 }}>{error}</Text>
            </div>
          ) : (
            <Text UNSAFE_style={{ marginTop: 12, fontSize: 12, color: 'var(--spectrum-gray-600)' }}>
              No credit card required · Free tier available
            </Text>
          )}
        </form>
        </View>
      </View>
    </section>
  )
}

function DemoSection() {
  return (
    <section id="demo" className={styles.sectionAnchor}>
      <View paddingY="size-600" backgroundColor="gray-75">
        <View UNSAFE_className={styles.max1152}>
          <View UNSAFE_className={styles.textCenter}>
            <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>DEMO PREVIEW</Text>
            <Heading level={2} marginTop="size-150">
              Summary output you can trust
            </Heading>
            <Text UNSAFE_style={{ marginTop: 12, maxWidth: 640, marginLeft: 'auto', marginRight: 'auto' }}>
              Every run produces structured takeaways, grounded in the transcript—not generic fluff.
            </Text>
          </View>

          <View
            marginTop="size-400"
            borderRadius="medium"
            overflow="hidden"
            borderWidth="thin"
            borderColor="gray-200"
            backgroundColor="gray-50"
          >
            <View padding="size-150" borderBottomWidth="thin" borderBottomColor="gray-200" backgroundColor="gray-75">
              <Flex direction="row" alignItems="center" gap="size-100">
                <View width="size-100" height="size-100" borderRadius="large" backgroundColor="red-400" UNSAFE_style={{ borderRadius: 9999 }} />
                <View width="size-100" height="size-100" borderRadius="large" backgroundColor="yellow-400" UNSAFE_style={{ borderRadius: 9999 }} />
                <View width="size-100" height="size-100" borderRadius="large" backgroundColor="green-400" UNSAFE_style={{ borderRadius: 9999 }} />
                <Text UNSAFE_style={{ flex: 1, textAlign: 'center', fontSize: 12, color: 'var(--spectrum-gray-500)' }}>
                  app / summarize · job completed
                </Text>
              </Flex>
            </View>
            <Grid columns={{ base: '1fr', L: '1fr 280px' }} gap={0}>
              <View padding="size-300" borderEndWidth={{ L: 'thin' }} borderEndColor={{ L: 'gray-200' }}>
                <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700 }}>SUMMARY</Text>
                <Heading level={3} marginTop="size-100">
                  How neural attention reshapes sequence modeling
                </Heading>
                <Text UNSAFE_style={{ marginTop: 16, lineHeight: 1.7 }}>
                  The video explains how self-attention lets models weigh every token against every other token, capturing
                  long-range dependencies that RNNs struggle with.
                </Text>
                <View marginTop="size-300">
                  <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700 }}>KEY TAKEAWAYS</Text>
                  <ul className={styles.demoBulletList}>
                    {[
                      'Attention is permutation-friendly: order is encoded via positions, not recurrence.',
                      'Scaled dot-product attention keeps gradients stable as dimensionality grows.',
                      'Multi-head attention is parallelizable and trains faster than deep recurrent stacks.',
                    ].map((line) => (
                      <li key={line} className={styles.demoBulletItem}>
                        <View
                          marginTop="size-65"
                          width="size-65"
                          height="size-65"
                          borderRadius="large"
                          backgroundColor="blue-500"
                          flexShrink={0}
                          UNSAFE_style={{ borderRadius: 9999 }}
                          aria-hidden
                        />
                        <Text>{line}</Text>
                      </li>
                    ))}
                  </ul>
                </View>
              </View>
              <View padding="size-300" backgroundColor="gray-75">
                <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700 }}>KEY MOMENTS</Text>
                <Flex direction="column" gap="size-150" marginTop="size-200">
                  {[
                    { t: '04:12', n: 'Intuition for why Q·Kᵀ measures alignment between positions.' },
                    { t: '12:40', n: 'Walkthrough of softmax weights as a differentiable lookup.' },
                  ].map((m) => (
                    <View key={m.t} padding="size-150" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
                      <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, color: 'var(--spectrum-blue-800)' }}>{m.t}</Text>
                      <Text UNSAFE_style={{ marginTop: 6, fontSize: 13 }}>{m.n}</Text>
                    </View>
                  ))}
                </Flex>
              </View>
            </Grid>
          </View>
        </View>
      </View>
    </section>
  )
}

const featureCards = [
  {
    title: 'Summary',
    body: 'Brief, bullet, or detailed modes. Titles, chapters, and key moments when the transcript allows.',
  },
  {
    title: 'Q&A',
    body: 'Ask grounded questions in chat. Answers stream in with citations you can jump to in the player.',
  },
  { title: 'Notes', body: 'Concise and detailed study notes plus a glossary—ready for revision and sharing.' },
  { title: 'Quiz', body: 'Auto-generated questions with explanations so you verify understanding—not just passively watch.' },
]

function FeaturesSection() {
  return (
    <section id="features" className={styles.sectionAnchor}>
      <View paddingY="size-600">
        <View UNSAFE_className={styles.max1152}>
          <View maxWidth="size-4600">
            <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>FEATURES</Text>
            <Heading level={2} marginTop="size-150">
              One pipeline from video to learning assets
            </Heading>
            <Text UNSAFE_style={{ marginTop: 12, fontSize: 18 }}>Built for students, creators, and teams who need signal—not a wall of transcript text.</Text>
          </View>
          <Grid columns={{ base: '1fr', S: 'repeat(2, 1fr)', L: 'repeat(4, 1fr)' }} gap="size-300" marginTop="size-400">
            {featureCards.map((f) => (
              <View key={f.title} padding="size-250" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
                <View
                  width="size-400"
                  height="size-400"
                  borderRadius="medium"
                  backgroundColor="gray-200"
                  UNSAFE_style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                >
                  <Text UNSAFE_style={{ fontWeight: 700 }}>{f.title[0]}</Text>
                </View>
                <Heading level={3} marginTop="size-200">
                  {f.title}
                </Heading>
                <Text UNSAFE_style={{ marginTop: 8, lineHeight: 1.55 }}>{f.body}</Text>
              </View>
            ))}
          </Grid>
        </View>
      </View>
    </section>
  )
}

function SocialProofSection() {
  return (
    <View
      paddingY="size-500"
      backgroundColor="gray-50"
      borderTopWidth="thin"
      borderBottomWidth="thin"
      borderColor="gray-200"
      UNSAFE_className={styles.pageGutter}
    >
      <View UNSAFE_className={`${styles.max1152} ${styles.textCenter}`}>
        <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>SOCIAL PROOF</Text>
        <Heading level={2} marginTop="size-150">
          Trusted by learners and teams (placeholder)
        </Heading>
        <Flex direction="row" gap="size-200" wrap justifyContent="center" marginTop="size-400">
          {['Acme Learn', 'Northwind U', 'Contoso Labs', 'Fabrikam AI'].map((name) => (
            <View
              key={name}
              padding="size-200"
              minWidth="size-2000"
              borderRadius="medium"
              borderWidth="thin"
              borderColor="gray-300"
              backgroundColor="gray-75"
              UNSAFE_style={{ borderStyle: 'dashed' }}
            >
              <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700 }}>{name}</Text>
            </View>
          ))}
        </Flex>
        <Grid columns={{ base: '1fr', M: 'repeat(3, 1fr)' }} gap="size-300" marginTop="size-400" maxWidth="size-6000" marginX="auto">
          {[
            { k: 'Summaries run', v: '12,400+', s: 'placeholder metric' },
            { k: 'Avg. time saved', v: '~40 min', s: 'per long video (est.)' },
            { k: 'Countries', v: '30+', s: 'placeholder reach' },
          ].map((row) => (
            <View key={row.k} padding="size-200" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-75">
              <Text UNSAFE_style={{ fontSize: 11, fontWeight: 600 }}>{row.k}</Text>
              <Heading level={3} marginTop="size-100">
                {row.v}
              </Heading>
              <Text UNSAFE_style={{ marginTop: 6, fontSize: 12, color: 'var(--spectrum-gray-600)' }}>{row.s}</Text>
            </View>
          ))}
        </Grid>
      </View>
    </View>
  )
}

function PricingSection() {
  return (
    <section id="pricing" className={styles.sectionAnchor}>
      <View paddingY="size-600">
        <View UNSAFE_className={`${styles.max1152} ${styles.textCenter}`}>
          <Text UNSAFE_style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.24em' }}>PRICING</Text>
          <Heading level={2} marginTop="size-150">
            Start free. Upgrade when you hit the wall.
          </Heading>
          <Text UNSAFE_style={{ marginTop: 12, maxWidth: 560, marginLeft: 'auto', marginRight: 'auto' }}>
            Same product surface on every tier—limits scale with you.
          </Text>
          <Grid columns={{ base: '1fr', L: '1fr 1fr' }} gap="size-300" marginTop="size-400">
            <View padding="size-300" borderRadius="medium" borderWidth="thin" borderColor="gray-200" backgroundColor="gray-50">
              <Text UNSAFE_style={{ fontWeight: 700 }}>Free</Text>
              <Heading level={3} marginTop="size-150">
                $0 / mo
              </Heading>
              <Text UNSAFE_style={{ marginTop: 12 }}>Full UI, capped summaries &amp; Q&amp;A—perfect to validate your workflow.</Text>
              <ul className={styles.pricingList}>
                <li>Dashboard, history, notes, quiz</li>
                <li>Standard transcript grounding</li>
              </ul>
              <Link to="/summarize" style={{ textDecoration: 'none', display: 'block', marginTop: 24 }}>
                <Button variant="secondary" width="100%">
                  Start with Free
                </Button>
              </Link>
            </View>
            <View
              padding="size-300"
              borderRadius="medium"
              borderWidth="thick"
              borderColor="blue-500"
              backgroundColor="static-blue-200"
              position="relative"
            >
              <View position="absolute" top="size-200" end="size-200" paddingX="size-150" paddingY="size-65" backgroundColor="blue-600" borderRadius="large" UNSAFE_style={{ borderRadius: 9999 }}>
                <Text UNSAFE_style={{ color: 'white', fontSize: 11, fontWeight: 700 }}>POPULAR</Text>
              </View>
              <Text UNSAFE_style={{ fontWeight: 700, color: 'var(--spectrum-blue-900)' }}>Pro</Text>
              <Heading level={3} marginTop="size-150">
                $19 / mo
              </Heading>
              <Text UNSAFE_style={{ marginTop: 12 }}>Unlimited usage, deeper retrieval, smarter compression, priority throughput.</Text>
              <ul className={styles.pricingList}>
                <li>Unlimited summaries &amp; Q&amp;A</li>
                <li>Advanced RAG &amp; exports</li>
              </ul>
              <Link to="/pricing" style={{ textDecoration: 'none', display: 'block', marginTop: 24 }}>
                <Button variant="accent" width="100%">
                  View full comparison
                </Button>
              </Link>
            </View>
          </Grid>
        </View>
      </View>
    </section>
  )
}

function FinalCTASection() {
  return (
    <View paddingBottom="size-600" UNSAFE_className={styles.pageGutter}>
      <View padding="size-500" borderRadius="large" backgroundColor="gray-900" UNSAFE_className={styles.ctaBand}>
        <Heading level={2} UNSAFE_className={styles.ctaTitle}>
          Ready to turn your next video into notes?
        </Heading>
        <Text UNSAFE_className={`${styles.ctaSub} ${styles.max520}`}>
          Join the workspace—paste a URL, run a job, and open Ask AI on the same transcript in one flow.
        </Text>
        <Flex direction={{ base: 'column', S: 'row' }} gap="size-150" justifyContent="center" marginTop="size-400">
          <Link to="/summarize" style={{ textDecoration: 'none' }}>
            <Button variant="primary" staticColor="white">
              Get started free
            </Button>
          </Link>
          <Link to="/dashboard" style={{ textDecoration: 'none' }}>
            <Button variant="secondary" staticColor="white">
              Open workspace
            </Button>
          </Link>
        </Flex>
      </View>
    </View>
  )
}

function LandingFooter() {
  return (
    <footer className={styles.pageGutter}>
      <View borderTopWidth="thin" borderTopColor="gray-200" backgroundColor="gray-75" paddingY="size-400">
        <Flex
          direction={{ base: 'column', S: 'row' }}
          justifyContent="space-between"
          alignItems="center"
          gap="size-300"
          UNSAFE_className={styles.max1152}
        >
          <Text UNSAFE_style={{ fontSize: 14, color: 'var(--spectrum-gray-600)' }}>
            © {new Date().getFullYear()} YouTube Copilot. All rights reserved.
          </Text>
          <Flex direction="row" gap="size-300">
            <Link to="/pricing" style={{ fontSize: 14, fontWeight: 500 }}>
              Pricing
            </Link>
            <Link to="/settings" style={{ fontSize: 14, fontWeight: 500 }}>
              Settings
            </Link>
            <Link to="/dashboard" style={{ fontSize: 14, fontWeight: 500 }}>
              App
            </Link>
          </Flex>
        </Flex>
      </View>
    </footer>
  )
}

export function LandingPage() {
  const navigate = useNavigate()
  const [url, setUrl] = useState('')
  const [error, setError] = useState<string | null>(null)

  function handleHeroSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    const trimmed = url.trim()
    if (!trimmed) {
      navigate('/summarize')
      return
    }
    if (!extractYouTubeVideoId(trimmed)) {
      setError('Please paste a valid YouTube watch or youtu.be link.')
      return
    }
    navigate('/summarize', { state: { url: trimmed } })
  }

  return (
    <View minHeight="100vh" backgroundColor="gray-75">
      <LandingNav />
      <main>
        <HeroSection url={url} setUrl={setUrl} error={error} onSubmit={handleHeroSubmit} />
        <DemoSection />
        <FeaturesSection />
        <SocialProofSection />
        <PricingSection />
        <FinalCTASection />
      </main>
      <LandingFooter />
    </View>
  )
}
