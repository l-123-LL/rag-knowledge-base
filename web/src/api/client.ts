import { findMockAnswer, mockSources } from '../data/mockData'
import type { Citation, FaqItem, Metrics, Source, Stats } from '../types'

export interface AskResponse {
  answer: string
  citations: Citation[]
  model: string
  status: 'done' | 'insufficient'
}

export interface IngestResponse {
  chunk_count: number
}

interface StreamHandlers {
  onSources?: (citations: Citation[]) => void
  onDelta?: (text: string) => void
}

// 模拟真实后端的响应时间，后续接 API 时只替换这个模块。
export const MOCK_DELAY_MS = 650

let sessionId: string | null = null

function getSessionId() {
  if (!sessionId) {
    sessionId =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(16).slice(2)}`
  }
  return sessionId
}

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

async function requestBackend(
  path: string,
  init?: RequestInit,
): Promise<Response | null> {
  if (typeof window === 'undefined' || typeof window.fetch !== 'function') {
    return null
  }

  try {
    const headers = new Headers(init?.headers)
    const adminApiKey = import.meta.env.VITE_ADMIN_API_KEY
    if (adminApiKey && !headers.has('X-API-Key')) {
      headers.set('X-API-Key', adminApiKey)
    }
    return await window.fetch(path, { ...init, headers })
  } catch {
    return null
  }
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const response = await requestBackend('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: getSessionId() }),
  })

  if (response?.ok) {
    return (await response.json()) as AskResponse
  }

  await wait(MOCK_DELAY_MS)
  const match = findMockAnswer(question)

  if (!match) {
    return {
      answer: '当前示例资料不足，暂时无法给出可靠回答。',
      citations: [],
      model: 'mock',
      status: 'insufficient',
    }
  }

  return {
    answer: match.answer,
    citations: match.citations,
    model: 'mock',
    status: 'done',
  }
}

export async function listSources(): Promise<Source[]> {
  const response = await requestBackend('/api/sources')

  if (response?.ok) {
    return (await response.json()) as Source[]
  }

  return mockSources
}

export async function getStats(): Promise<Stats> {
  const response = await requestBackend('/api/stats')

  if (response?.ok) {
    return (await response.json()) as Stats
  }

  return {
    source_count: mockSources.length,
    chunk_count: 0,
    session_count: 0,
    faq_count: 0,
  }
}

export async function getMetrics(): Promise<Metrics> {
  const response = await requestBackend('/api/metrics')

  if (response?.ok) {
    return (await response.json()) as Metrics
  }

  return {
    total_queries: 0,
    route_counts: {},
    avg_latency_ms: 0,
    total_tokens: 0,
    total_cost: 0,
    feedback_count: 0,
    helpful_rate: 0,
  }
}

export async function createFaq(payload: {
  question: string
  answer: string
  keywords: string[]
}): Promise<FaqItem> {
  const response = await requestBackend('/faqs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, source: '前端录入' }),
  })

  if (!response) {
    throw new Error('后端不可用')
  }

  if (!response.ok) {
    throw new Error('FAQ 创建失败')
  }

  return (await response.json()) as FaqItem
}

export async function ingestFile(file: File): Promise<IngestResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const response = await requestBackend('/ingest/file', {
    method: 'POST',
    body: formData,
  })

  if (!response) {
    throw new Error('后端不可用')
  }

  if (!response.ok) {
    throw new Error('上传失败')
  }

  return (await response.json()) as IngestResponse
}

export async function ingestUrl(url: string): Promise<IngestResponse> {
  const response = await requestBackend('/ingest/url', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })

  if (!response) {
    throw new Error('后端不可用')
  }

  if (!response.ok) {
    throw new Error('网页导入失败')
  }

  return (await response.json()) as IngestResponse
}

export async function streamAsk(
  question: string,
  handlers: StreamHandlers,
): Promise<void> {
  if (typeof window === 'undefined' || typeof window.fetch !== 'function') {
    throw new Error('当前环境不支持流式输出')
  }

  const response = await window.fetch('/api/ask/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: getSessionId() }),
  })

  if (!response.ok || !response.body) {
    throw new Error('流式接口不可用')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) {
        continue
      }

      const data = trimmed.slice(5).trim()
      if (data === '[DONE]') {
        return
      }

      const payload = JSON.parse(data) as {
        type: string
        text?: string
        contexts?: Array<{
          text: string
          source: string
          score: number
        }>
      }

      if (payload.type === 'delta' && payload.text) {
        handlers.onDelta?.(payload.text)
      }

      if (payload.type === 'sources' && payload.contexts) {
        handlers.onSources?.(
          payload.contexts.map((context, index) => ({
            id: `stream-${index}`,
            title: context.source,
            url: '',
            location: '',
            snippet: context.text,
            score: context.score,
          })),
        )
      }
    }
  }
}

export async function resetSession(): Promise<void> {
  const currentSessionId = sessionId
  sessionId = null

  if (!currentSessionId) {
    return
  }

  await requestBackend('/session/reset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: currentSessionId }),
  })
}

export async function archiveSource(
  sourceId: string,
  archived: boolean,
): Promise<Source> {
  const response = await requestBackend(
    `/sources/${encodeURIComponent(sourceId)}/archive?archived=${archived}`,
    { method: 'POST' },
  )

  if (!response) {
    throw new Error('后端不可用')
  }

  if (!response.ok) {
    throw new Error('来源状态更新失败')
  }

  return (await response.json()) as Source
}

export async function sendFeedback(payload: {
  question: string
  rating: 'up' | 'down'
}): Promise<void> {
  const response = await requestBackend('/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response) {
    throw new Error('后端不可用')
  }

  if (!response.ok) {
    throw new Error('反馈提交失败')
  }
}
