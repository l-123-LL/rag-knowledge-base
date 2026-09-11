export type SourceStatus = 'indexed' | 'pending' | 'failed'

export interface Source {
  id: string
  title: string
  category: string
  url: string
  status: SourceStatus
  updatedAt: string
  description: string
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
