import { describe, expect, it } from 'vitest'
import { findMockAnswer, mockConversations } from './mockData'

describe('findMockAnswer', () => {
  it('returns a matching sample for a known customer service question', () => {
    const result = findMockAnswer('如何申请退货？')

    expect(result?.id).toBe('return-policy')
    expect(result?.citations.length).toBeGreaterThan(0)
  })

  it('does not match unrelated content', () => {
    expect(findMockAnswer('今天天气如何')).toBeUndefined()
  })

  it('keeps the sample question list non-empty', () => {
    expect(mockConversations.length).toBeGreaterThanOrEqual(3)
  })
})
