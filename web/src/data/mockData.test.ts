import { describe, expect, it } from 'vitest'
import { findMockAnswer, mockConversations } from './mockData'

describe('findMockAnswer', () => {
  it('returns a matching sample for a known medical question', () => {
    const result = findMockAnswer('成人流感的抗病毒治疗时机是什么？')

    expect(result?.id).toBe('flu-treatment')
    expect(result?.citations.length).toBeGreaterThan(0)
  })

  it('does not match unrelated content', () => {
    expect(findMockAnswer('今天天气如何')).toBeUndefined()
  })

  it('keeps the sample question list non-empty', () => {
    expect(mockConversations.length).toBeGreaterThanOrEqual(3)
  })
})
