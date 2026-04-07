/** Client-side usage and recent-video hints until a backend tenant API exists. */

const STATS_KEY = 'ycopilot_usage_stats_v1'
const RECENT_KEY = 'ycopilot_recent_videos_v1'
const QUOTA_PERIOD_KEY = 'ycopilot_quota_period_v1'
const PLAN_KEY = 'ycopilot_plan_v1'
const MAX_RECENT = 24

/** Aligns with pricing copy: Free tier monthly caps (browser-local until billing exists). */
export const FREE_TIER_VIDEO_LIMIT_MONTHLY = 5
export const FREE_TIER_QUESTION_LIMIT_MONTHLY = 20

export type BillingPlan = 'free' | 'pro'

export type UsageStats = {
  videosProcessed: number
  questionsAsked: number
}

export type QuotaSnapshot = {
  plan: BillingPlan
  periodKey: string
  videosUsed: number
  questionsUsed: number
  /** `null` when plan is Pro (unlimited). */
  videosRemaining: number | null
  questionsRemaining: number | null
  videoLimit: number
  questionLimit: number
  videosAtLimit: boolean
  questionsAtLimit: boolean
  anyAtLimit: boolean
}

type QuotaPeriodRow = {
  periodKey: string
  videos: number
  questions: number
}

export type RecentVideoLocal = {
  videoId: string
  url: string
  title: string
  processedAt: string
}

function safeParse<T>(raw: string | null, fallback: T): T {
  if (raw == null || raw === '') return fallback
  try {
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

export function readUsageStats(): UsageStats {
  const v = safeParse<Partial<UsageStats>>(localStorage.getItem(STATS_KEY), {})
  return {
    videosProcessed: Math.max(0, Number(v.videosProcessed) || 0),
    questionsAsked: Math.max(0, Number(v.questionsAsked) || 0),
  }
}

function writeUsageStats(s: UsageStats) {
  localStorage.setItem(STATS_KEY, JSON.stringify(s))
}

function currentPeriodKey(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function readQuotaPeriodRow(): QuotaPeriodRow {
  const parsed = safeParse<Partial<QuotaPeriodRow>>(localStorage.getItem(QUOTA_PERIOD_KEY), {})
  const key = currentPeriodKey()
  if (parsed.periodKey !== key) {
    return { periodKey: key, videos: 0, questions: 0 }
  }
  return {
    periodKey: key,
    videos: Math.max(0, Number(parsed.videos) || 0),
    questions: Math.max(0, Number(parsed.questions) || 0),
  }
}

function writeQuotaPeriodRow(row: QuotaPeriodRow) {
  localStorage.setItem(QUOTA_PERIOD_KEY, JSON.stringify(row))
}

function bumpQuotaVideo() {
  const key = currentPeriodKey()
  let row = readQuotaPeriodRow()
  if (row.periodKey !== key) {
    row = { periodKey: key, videos: 0, questions: 0 }
  }
  row.videos += 1
  writeQuotaPeriodRow(row)
}

function bumpQuotaQuestion() {
  const key = currentPeriodKey()
  let row = readQuotaPeriodRow()
  if (row.periodKey !== key) {
    row = { periodKey: key, videos: 0, questions: 0 }
  }
  row.questions += 1
  writeQuotaPeriodRow(row)
}

export function readBillingPlan(): BillingPlan {
  const raw = localStorage.getItem(PLAN_KEY)
  if (raw == null || raw === '') return 'free'
  try {
    const v: unknown = JSON.parse(raw)
    return v === 'pro' ? 'pro' : 'free'
  } catch {
    return raw === 'pro' ? 'pro' : 'free'
  }
}

/** Session flag: user dismissed the free-tier limit modal (same tab). */
export const UPGRADE_MODAL_DISMISS_SESSION_KEY = 'ycopilot_upgrade_modal_dismissed'

export function setBillingPlan(plan: BillingPlan) {
  localStorage.setItem(PLAN_KEY, JSON.stringify(plan))
  if (plan === 'pro') {
    try {
      sessionStorage.removeItem(UPGRADE_MODAL_DISMISS_SESSION_KEY)
    } catch {
      /* private mode */
    }
  }
  notifyUsageChanged()
}

export function readQuotaSnapshot(): QuotaSnapshot {
  const plan = readBillingPlan()
  const row = readQuotaPeriodRow()
  const periodKey = row.periodKey

  if (plan === 'pro') {
    return {
      plan: 'pro',
      periodKey,
      videosUsed: row.videos,
      questionsUsed: row.questions,
      videosRemaining: null,
      questionsRemaining: null,
      videoLimit: FREE_TIER_VIDEO_LIMIT_MONTHLY,
      questionLimit: FREE_TIER_QUESTION_LIMIT_MONTHLY,
      videosAtLimit: false,
      questionsAtLimit: false,
      anyAtLimit: false,
    }
  }

  const vRem = Math.max(0, FREE_TIER_VIDEO_LIMIT_MONTHLY - row.videos)
  const qRem = Math.max(0, FREE_TIER_QUESTION_LIMIT_MONTHLY - row.questions)
  const vAt = row.videos >= FREE_TIER_VIDEO_LIMIT_MONTHLY
  const qAt = row.questions >= FREE_TIER_QUESTION_LIMIT_MONTHLY

  return {
    plan: 'free',
    periodKey,
    videosUsed: row.videos,
    questionsUsed: row.questions,
    videosRemaining: vRem,
    questionsRemaining: qRem,
    videoLimit: FREE_TIER_VIDEO_LIMIT_MONTHLY,
    questionLimit: FREE_TIER_QUESTION_LIMIT_MONTHLY,
    videosAtLimit: vAt,
    questionsAtLimit: qAt,
    anyAtLimit: vAt || qAt,
  }
}

/** Stable snapshot reference for `useSyncExternalStore` (avoids infinite re-renders). */
let quotaSnapshotCache: { signature: string; snapshot: QuotaSnapshot } | null = null

export function getQuotaSnapshotForSync(): QuotaSnapshot {
  const next = readQuotaSnapshot()
  const signature = JSON.stringify(next)
  if (quotaSnapshotCache && quotaSnapshotCache.signature === signature) {
    return quotaSnapshotCache.snapshot
  }
  quotaSnapshotCache = { signature, snapshot: next }
  return next
}

function notifyUsageChanged() {
  window.dispatchEvent(new Event('ycopilot-usage'))
}

export function subscribeUsage(listener: () => void) {
  const wrapped = () => listener()
  window.addEventListener('storage', wrapped)
  window.addEventListener('ycopilot-usage', wrapped)
  return () => {
    window.removeEventListener('storage', wrapped)
    window.removeEventListener('ycopilot-usage', wrapped)
  }
}

export function incrementVideosProcessed(): UsageStats {
  bumpQuotaVideo()
  notifyUsageChanged()
  const cur = readUsageStats()
  const next = { ...cur, videosProcessed: cur.videosProcessed + 1 }
  writeUsageStats(next)
  return next
}

export function incrementQuestionsAsked(): UsageStats {
  bumpQuotaQuestion()
  notifyUsageChanged()
  const cur = readUsageStats()
  const next = { ...cur, questionsAsked: cur.questionsAsked + 1 }
  writeUsageStats(next)
  return next
}

export function readRecentVideosLocal(): RecentVideoLocal[] {
  const list = safeParse<unknown>(localStorage.getItem(RECENT_KEY), [])
  if (!Array.isArray(list)) return []
  return list
    .filter(
      (x): x is RecentVideoLocal =>
        x != null &&
        typeof x === 'object' &&
        typeof (x as RecentVideoLocal).videoId === 'string' &&
        typeof (x as RecentVideoLocal).url === 'string' &&
        typeof (x as RecentVideoLocal).title === 'string',
    )
    .slice(0, MAX_RECENT)
}

export function prependRecentVideo(entry: Omit<RecentVideoLocal, 'processedAt'>): void {
  const at = new Date().toISOString()
  const row: RecentVideoLocal = { ...entry, processedAt: at }
  const prev = readRecentVideosLocal().filter((r) => r.videoId !== entry.videoId)
  const next = [row, ...prev].slice(0, MAX_RECENT)
  localStorage.setItem(RECENT_KEY, JSON.stringify(next))
}
