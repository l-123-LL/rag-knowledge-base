import { findMockAnswer, mockSources } from '../data/mockData'
import type { Citation, Source } from '../types'

export interface AskResponse {
  answer: string
  citations: Citation[]
  model: string
  status: 'done' | 'insufficient'
}

export interface IngestResponse {
  chunk_count: number
}

// 模拟真实后端的响应时间，后续接 API 时只替换这个模块。
export const MOCK_DELAY_MS = 650

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
    return await window.fetch(path, init)
  } catch {
    return null
  }
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const response = await requestBackend('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
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
