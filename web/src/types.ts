export type SourceStatus = 'indexed' | 'pending' | 'failed'

export interface Source {
  id: string
  title: string
  category: string
  url: string
  status: SourceStatus
  updatedAt: string
  description: string
  archived?: boolean
}

export interface Stats {
  source_count: number
  chunk_count: number
  session_count: number
  faq_count: number
}

export interface Metrics {
  total_queries: number
  route_counts: Record<string, number>
  avg_latency_ms: number
  total_tokens: number
  total_cost: number
}

export interface FaqItem {
  id: string
  question: string
  answer: string
  keywords: string[]
}

export interface Citation {
  id: string
  title: string
  url: string
  location: string
  snippet: string
  score: number
}

export type ConversationStatus = 'loading' | 'done' | 'insufficient'

export interface Conversation {
  id: string
  question: string
  answer?: string
  citations: Citation[]
  status: ConversationStatus
}

export interface MockConversation {
  id: string
  question: string
  keywords: string[]
  answer: string
  citations: Citation[]
}
