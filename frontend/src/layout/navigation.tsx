import type { ReactElement, SVGProps } from 'react'

type IconProps = SVGProps<SVGSVGElement>

export type AssistantContent = {
  eyebrow: string
  title: string
  description: string
  bullets: string[]
  footer: string
}

export type NavigationItem = {
  id: string
  label: string
  path: string
  description: string
  icon: (props: IconProps) => ReactElement
  assistant?: AssistantContent
}

function DashboardIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M4 13.5h6.5V20H4zM13.5 4H20v9.5h-6.5zM13.5 16.5H20V20h-6.5zM4 4h6.5v6.5H4z" />
    </svg>
  )
}

function HistoryIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M12 7v5l3 2" />
      <path d="M4 12a8 8 0 1 0 2.34-5.66" />
      <path d="M4 4v4h4" />
    </svg>
  )
}

function SparkIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="m12 2 2.1 5.4L19.5 9l-5.4 2.1L12 16.5l-2.1-5.4L4.5 9l5.4-1.6L12 2Z" />
      <path d="m18 15 1 2.5 2.5 1L19 19.5 18 22l-1-2.5-2.5-1 2.5-1Z" />
    </svg>
  )
}

function AskIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M6 16.5 3 21l5-2a9 9 0 1 0-2-2.5Z" />
      <path d="M12 8h.01M9.5 12a2.5 2.5 0 0 1 5 0c0 1.7-2.5 2-2.5 4" />
    </svg>
  )
}

function NotesIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M6 3.5h9l3 3V20a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-15a1 1 0 0 1 1-1Z" />
      <path d="M9 9h6M9 13h6M9 17h4" />
    </svg>
  )
}

function QuizIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M9 9a3 3 0 1 1 5.2 2l-1.2 1.2a2 2 0 0 0-.6 1.4v.4" />
      <path d="M12 18h.01" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  )
}

function FlashcardsIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <rect x="7" y="5" width="12" height="14" rx="2" />
      <path d="M7 8H5a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h10" />
      <path d="M10 10h6M10 14h4" />
    </svg>
  )
}

function PricingIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M4 7.5h16v9H4z" />
      <path d="M7 10.5h5M7 13.5h3" strokeLinecap="round" />
      <path d="M15 12.5h2" strokeLinecap="round" />
    </svg>
  )
}

function SettingsIcon(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" {...props}>
      <path d="M12 15.5A3.5 3.5 0 1 0 12 8.5a3.5 3.5 0 0 0 0 7Z" />
      <path d="M19.4 15a1 1 0 0 0 .2 1.1l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1 1 0 0 0-1.1-.2 1 1 0 0 0-.6.9V20a2 2 0 1 1-4 0v-.2a1 1 0 0 0-.7-.9 1 1 0 0 0-1.1.2l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1 1 0 0 0 .2-1.1 1 1 0 0 0-.9-.6H4a2 2 0 1 1 0-4h.2a1 1 0 0 0 .9-.7 1 1 0 0 0-.2-1.1l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1 1 0 0 0 1.1.2 1 1 0 0 0 .6-.9V4a2 2 0 1 1 4 0v.2a1 1 0 0 0 .7.9 1 1 0 0 0 1.1-.2l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1 1 0 0 0-.2 1.1 1 1 0 0 0 .9.6H20a2 2 0 1 1 0 4h-.2a1 1 0 0 0-.9.7Z" />
    </svg>
  )
}

export const navigationItems: NavigationItem[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    path: '/dashboard',
    description: 'Overview, quick actions, and recent activity.',
    icon: DashboardIcon,
    assistant: {
      eyebrow: 'Overview',
      title: 'Command center',
      description: 'Track the product at a glance and jump into the next workflow without leaving the shell.',
      bullets: [
        'Recent summaries surface engagement-ready context.',
        'Feature cards keep the main product areas one click away.',
        'The layout is optimized for a multi-workflow SaaS feel on desktop and mobile.',
      ],
      footer: 'Use the global search to jump between pages quickly.',
    },
  },
  {
    id: 'history',
    label: 'History',
    path: '/history',
    description: 'Browse recently generated summaries and revisit videos.',
    icon: HistoryIcon,
    assistant: {
      eyebrow: 'Audit trail',
      title: 'Recent work at your fingertips',
      description: 'History acts like a lightweight workspace index so teams can continue where they left off.',
      bullets: [
        'Every row surfaces summary type, language, and transcript size.',
        'Cards are responsive and easy to scan on smaller screens.',
        'The same SaaS surfaces carry through from dashboard to detail views.',
      ],
      footer: 'This page is ready for filters, starring, or saved workspaces later.',
    },
  },
  {
    id: 'summarize',
    label: 'Summarize',
    path: '/summarize',
    description: 'Run async video summarization and review key moments.',
    icon: SparkIcon,
    assistant: {
      eyebrow: 'Async pipeline',
      title: 'Long videos no longer block the UI',
      description: 'The summarize page now matches the backend job model and polls for status updates behind the scenes.',
      bullets: [
        'Submit once and the page tracks queued, running, completed, or failed states.',
        'Key moments, chapters, and suggested questions render when the job completes.',
        'The player stays visible so the experience feels like a real workspace, not a form.',
      ],
      footer: 'Use suggested questions to branch directly into Ask AI.',
    },
  },
  {
    id: 'ask-ai',
    label: 'Ask AI',
    path: '/ask-ai',
    description: 'Ask grounded questions about a YouTube video.',
    icon: AskIcon,
    assistant: {
      eyebrow: 'Conversational workflow',
      title: 'Streaming answers with sources',
      description: 'Ask AI is centered around a chat canvas while the global shell keeps navigation and context stable.',
      bullets: [
        'Starter prompts reduce blank-state friction.',
        'Streaming responses keep the app feeling responsive.',
        'Source timestamps remain actionable from inside the chat.',
      ],
      footer: 'This panel is intentionally optional so the main canvas keeps focus.',
    },
  },
  {
    id: 'notes',
    label: 'Notes',
    path: '/notes',
    description: 'Generate concise notes and glossary items.',
    icon: NotesIcon,
    assistant: {
      eyebrow: 'Study mode',
      title: 'Readable notes, fast',
      description: 'Notes are laid out like a polished knowledge workspace instead of a raw text dump.',
      bullets: [
        'Concise and detailed notes are separated for easy scanning.',
        'Glossary terms are broken into digestible cards.',
        'The page layout works equally well for self-study or team handoff.',
      ],
      footer: 'The same shell can scale to exporting and saved note bundles later.',
    },
  },
  {
    id: 'quiz',
    label: 'Quiz',
    path: '/quiz',
    description: 'Turn transcript content into structured quiz questions.',
    icon: QuizIcon,
    assistant: {
      eyebrow: 'Assessment',
      title: 'Practice comprehension quickly',
      description: 'Quiz results are shown in a card stack that feels at home in a modern admin product.',
      bullets: [
        'Each question keeps options, answer, and explanation together.',
        'Spacing supports long-form study content without looking crowded.',
        'The route is isolated, making future grading or analytics easy to add.',
      ],
      footer: 'A dedicated quiz route keeps educational workflows distinct from chat.',
    },
  },
  {
    id: 'flashcards',
    label: 'Flashcards',
    path: '/flashcards',
    description: 'Review core concepts in a card-first format.',
    icon: FlashcardsIcon,
    assistant: {
      eyebrow: 'Retention',
      title: 'Cards built for repetition',
      description: 'Flashcards use a visual grid so the page feels productized rather than improvised.',
      bullets: [
        'Front and back content are separated with strong typography.',
        'Timestamp metadata can be surfaced as learning anchors.',
        'The same shell keeps the workflow discoverable from anywhere.',
      ],
      footer: 'This route can later support spaced repetition or saved decks.',
    },
  },
  {
    id: 'pricing',
    label: 'Pricing',
    path: '/pricing',
    description: 'Compare Free and Pro plans and upgrade when you are ready.',
    icon: PricingIcon,
    assistant: {
      eyebrow: 'Monetization',
      title: 'Plans that scale with usage',
      description: 'Pricing is presented like a production SaaS: clear tiers, comparison table, and a highlighted Pro tier.',
      bullets: [
        'Free keeps the full UI with honest usage limits.',
        'Pro emphasizes unlimited workflows and advanced copilot features.',
        'Upgrade CTA is ready for Stripe or a billing portal later.',
      ],
      footer: 'Use this page in demos to discuss unit economics and packaging.',
    },
  },
  {
    id: 'settings',
    label: 'Settings',
    path: '/settings',
    description: 'Inspect configuration and personalize the workspace.',
    icon: SettingsIcon,
    assistant: {
      eyebrow: 'Administration',
      title: 'Control the workspace',
      description: 'Settings combines backend config visibility with product-level preferences inside the same shell.',
      bullets: [
        'Environment details are surfaced without exposing secrets.',
        'Preference controls are grouped into readable admin cards.',
        'The layout leaves room for team, billing, or audit settings later.',
      ],
      footer: 'A strong shell makes even basic settings feel credible and complete.',
    },
  },
]
