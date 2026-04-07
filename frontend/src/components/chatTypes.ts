import type { AskSource } from '../api/types'

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  /** Unix ms when the message was finalized or first shown */
  createdAt?: number
  confidence?: number
  sources?: AskSource[]
  /** True while tokens are still arriving; final ``done`` clears this. */
  isStreaming?: boolean
}
