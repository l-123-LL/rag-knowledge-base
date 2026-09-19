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
  ticket_count: number
}

export interface Metrics {
  total_queries: number
  route_counts: Record<string, number>
  avg_latency_ms: number
  total_tokens: number
  total_cost: number
  feedback_count: number
  helpful_rate: number
}

export interface FaqItem {
  id: string
  question: string
  answer: string
  keywords: string[]
  version?: number
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

export type WorkflowMode = 'rag' | 'tools'

export interface TraceStep {
  step: number
  action: string
  tool?: string
  status?: string
  code?: string
  attempts?: number
  duration_ms?: number
  input_summary?: string
  intent?: string
  matched?: string
  reason?: string
}

export interface TraceRecord {
  trace_id: string
  tenant_id: string
  question: string
  intent?: string
  mode?: string
  model?: string
  steps: TraceStep[]
  tool_calls?: number
  citation_count?: number
  usage?: Record<string, number> | null
  cost?: number | null
  latency_ms?: number
  status?: string
  handoff_reason?: string | null
  created_at?: string
}

export type ApprovalStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'executed'
  | 'failed'

export interface ApprovalRecord {
  id: string
  tool: string
  status: ApprovalStatus
  tenant_id?: string
  created_at?: string
  decided_by?: string | null
  decision_comment?: string | null
  preview?: Record<string, unknown>
  execution?: {
    ok: boolean
    code: string
    data?: Record<string, unknown> | null
  } | null
}

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
