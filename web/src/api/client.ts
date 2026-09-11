import { findMockAnswer, mockSources } from '../data/mockData'
import type { Citation, Source } from '../types'

export interface AskResponse {
  answer: string
  citations: Citation[]
  model: string
  status: 'done' | 'insufficient'
}

// 模拟真实后端的响应时间，后续接 API 时只替换这个模块。
export const MOCK_DELAY_MS = 650

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

export async function askQuestion(question: string): Promise<AskResponse> {
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
  return mockSources
}
