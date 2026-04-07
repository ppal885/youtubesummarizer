export type SummaryType = 'brief' | 'detailed' | 'bullet' | 'technical'

export interface PublicLlmConfig {
  provider: string
  model: string
  configured: boolean
  base_url_custom: boolean
  json_response_format: boolean
}

export interface PublicConfigResponse {
  app_name: string
  app_version: string
  llm: PublicLlmConfig
  demo_mode?: boolean
  demo_sample_video_url?: string | null
}

export type LearningLevel = 'beginner' | 'intermediate' | 'advanced'

export interface SummarizeRequestBody {
  url: string
  summary_type: SummaryType
  language: string
  learning_level?: LearningLevel
  developer_mode?: boolean
}

export type SummaryJobState = 'queued' | 'running' | 'completed' | 'failed'

export interface SummaryJobAcceptedResponse {
  job_id: string
  status: SummaryJobState
  status_url: string
}

export interface SummaryJobError {
  stage?: string | null
  type: string
  detail: string
}

export interface SummaryJobStatusResponse {
  job_id: string
  status: SummaryJobState
  source_url: string
  summary_type: string
  language: string
  video_id?: string | null
  summary_result_id?: number | null
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  result?: FinalSummary | null
  error?: SummaryJobError | null
}

export interface KeyMoment {
  time: string
  note: string
}

export interface VideoChapter {
  title: string
  start_time: number
  formatted_time: string
  short_summary: string
}

/** Developer-mode extraction (snake_case matches API JSON). */
export interface DeveloperStudyDigest {
  concepts: string[]
  tools: string[]
  patterns: string[]
  best_practices: string[]
  pitfalls: string[]
  pseudo_code: string
  explanation: string
}

export interface FinalSummary {
  video_id: string
  title: string
  summary: string
  bullets: string[]
  key_moments: KeyMoment[]
  transcript_length: number
  chunks_processed: number
  learning_level?: LearningLevel
  /** From API (LLM); UI falls back to client-built chips if missing/empty. */
  suggested_questions?: string[]
  /** Topic-based sections (may be empty or a single entry when segmentation is uncertain). */
  chapters?: VideoChapter[]
  /** Present when the summarize request used developer_mode. */
  developer_digest?: DeveloperStudyDigest | null
}

export interface AskRequestBody {
  url: string
  question: string
  /** Optional; default en on the server */
  language?: string
}

export interface AskSource {
  start_time: number
  formatted_time: string
  text: string
}

export interface AskResponse {
  answer: string
  sources: AskSource[]
  confidence: number
}

export interface StoredSummaryListItem {
  id: number
  video_id: string
  source_url: string
  summary_type: string
  language: string
  title: string
  transcript_length: number
  chunks_processed: number
  created_at: string
}

/** Body for POST /api/v1/notes, /quiz, /flashcards */
export interface TranscriptLearningRequestBody {
  url: string
  language?: string
}

export interface GlossaryTerm {
  term: string
  definition: string
}

export interface NotesResponse {
  video_id: string
  title: string
  concise_notes: string
  detailed_notes: string
  glossary_terms: GlossaryTerm[]
}

export interface QuizQuestionItem {
  question: string
  options: [string, string, string, string]
  answer: string
  explanation: string
}

export interface QuizResponse {
  video_id: string
  title: string
  questions: QuizQuestionItem[]
}

export interface FlashcardItem {
  front: string
  back: string
  timestamp_seconds?: number | null
  formatted_time?: string | null
}

export interface FlashcardsResponse {
  video_id: string
  title: string
  cards: FlashcardItem[]
}
