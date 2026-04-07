import type { FinalSummary } from '../api/types'

export type SuggestedQuestionCategory = 'basics' | 'deep_dive' | 'practical'

export type SuggestedQuestionItem = {
  text: string
  category: SuggestedQuestionCategory
}

/** Hard cap for chip count (requirements: 6–8). */
export const SUGGESTED_QUESTIONS_MAX = 8

const CATEGORY_ORDER: SuggestedQuestionCategory[] = ['basics', 'deep_dive', 'practical']

export function dedupeSuggestedItems(items: SuggestedQuestionItem[]): SuggestedQuestionItem[] {
  const seen = new Set<string>()
  return items.filter((x) => {
    const k = x.text.toLowerCase().trim()
    if (!k || seen.has(k)) return false
    seen.add(k)
    return true
  })
}

function inferCategoryFromText(text: string): SuggestedQuestionCategory {
  const t = text.toLowerCase()
  if (
    /\b(should|actionable|do next|apply|try|practice|implement|concrete step|pay attention|watch)\b/.test(t) ||
    /\bhow can i\b/.test(t)
  ) {
    return 'practical'
  }
  if (
    /\b(explain|why\b|further|deeper|how does|detail|nuance|discussed around)\b/.test(t) ||
    /^explain further:/i.test(text) ||
    text.length > 100
  ) {
    return 'deep_dive'
  }
  return 'basics'
}

/** Spread API-provided strings across categories, then keep at most `SUGGESTED_QUESTIONS_MAX`. */
export function categorizePlainQuestionStrings(strings: string[]): SuggestedQuestionItem[] {
  const tagged = strings.map((text) => ({
    text: text.trim(),
    category: inferCategoryFromText(text),
  }))
  const deduped = dedupeSuggestedItems(tagged.filter((x) => x.text.length > 0))
  return pickBalancedByCategory(deduped, SUGGESTED_QUESTIONS_MAX)
}

function pickBalancedByCategory(items: SuggestedQuestionItem[], max: number): SuggestedQuestionItem[] {
  const buckets: Record<SuggestedQuestionCategory, SuggestedQuestionItem[]> = {
    basics: [],
    deep_dive: [],
    practical: [],
  }
  for (const item of items) {
    buckets[item.category].push(item)
  }
  const out: SuggestedQuestionItem[] = []
  let round = 0
  while (out.length < max && CATEGORY_ORDER.some((c) => buckets[c].length > round)) {
    for (const c of CATEGORY_ORDER) {
      if (out.length >= max) break
      const row = buckets[c][round]
      if (row) out.push(row)
    }
    round += 1
  }
  return out
}

/** Derive categorized chips from summary + API fields (no extra LLM call). */
export function buildSuggestedQuestions(summary: FinalSummary): SuggestedQuestionItem[] {
  const basics: SuggestedQuestionItem[] = [
    { text: 'What is this video mainly about?', category: 'basics' },
    { text: 'What are the most important conclusions?', category: 'basics' },
    { text: 'Who is the intended audience?', category: 'basics' },
  ]
  const fromMoments = summary.key_moments.slice(0, 2).map((m) => ({
    text: `What is discussed around ${m.time}?`,
    category: 'deep_dive' as const,
  }))
  const fromBullets = summary.bullets.slice(0, 3).map((b) => {
    const short = b.length > 72 ? `${b.slice(0, 69)}…` : b
    return { text: `Explain further: ${short}`, category: 'deep_dive' as const }
  })
  const practical: SuggestedQuestionItem[] = [
    { text: 'Is there anything actionable I should do next?', category: 'practical' },
  ]
  const merged = dedupeSuggestedItems([...basics, ...fromMoments, ...fromBullets, ...practical])
  return pickBalancedByCategory(merged, SUGGESTED_QUESTIONS_MAX)
}

/** Curated starter chips for Ask AI when no summary context is available (6–7 items). */
export const ASK_AI_STARTER_ITEMS: SuggestedQuestionItem[] = [
  { text: 'What are the biggest takeaways from this video?', category: 'basics' },
  { text: 'What is the main argument or thesis?', category: 'basics' },
  { text: 'Who is this video best suited for?', category: 'basics' },
  { text: 'Can you explain the core idea in plain English?', category: 'deep_dive' },
  { text: 'What nuance or caveat does the speaker emphasize?', category: 'deep_dive' },
  { text: 'What should I pay attention to on a second watch?', category: 'practical' },
  { text: 'What is one concrete step I could take after watching?', category: 'practical' },
]

export function buildAskAiDisplayItems(routeQuestion: string | undefined): SuggestedQuestionItem[] {
  const base = [...ASK_AI_STARTER_ITEMS]
  if (!routeQuestion?.trim()) {
    return pickBalancedByCategory(dedupeSuggestedItems(base), SUGGESTED_QUESTIONS_MAX)
  }
  const q = routeQuestion.trim()
  const head: SuggestedQuestionItem = { text: q, category: inferCategoryFromText(q) }
  const rest = base.filter((x) => x.text.toLowerCase() !== q.toLowerCase())
  return pickBalancedByCategory(dedupeSuggestedItems([head, ...rest]), SUGGESTED_QUESTIONS_MAX)
}
