import { describe, expect, it, vi } from 'vitest'
import { askQuestion, MOCK_DELAY_MS, listSources } from './client'

describe('api client', () => {
  it('returns a grounded mock answer for a matching question', async () => {
    vi.useFakeTimers()

    const request = askQuestion('成人流感的抗病毒治疗时机是什么？')
    await vi.advanceTimersByTimeAsync(MOCK_DELAY_MS)
    const response = await request

    expect(response.status).toBe('done')
    expect(response.answer).toContain('抗流感病毒治疗')
    expect(response.citations.length).toBeGreaterThan(0)

    vi.useRealTimers()
  })

  it('returns insufficient data when no sample matches', async () => {
    vi.useFakeTimers()

    const request = askQuestion('今天天气如何')
    await vi.advanceTimersByTimeAsync(MOCK_DELAY_MS)
    const response = await request

    expect(response.status).toBe('insufficient')
    expect(response.citations).toEqual([])

    vi.useRealTimers()
  })

  it('lists the local sample sources', async () => {
    const sources = await listSources()

    expect(sources.length).toBeGreaterThan(0)
  })
})
