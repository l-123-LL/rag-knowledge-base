import { describe, expect, it, vi } from 'vitest'
import {
  askQuestion,
  ingestUrl,
  MOCK_DELAY_MS,
  listSources,
  resetSession,
} from './client'

describe('api client', () => {
  it('returns a grounded mock answer for a matching question', async () => {
    vi.useFakeTimers()

    const request = askQuestion('如何申请退货？')
    await vi.advanceTimersByTimeAsync(MOCK_DELAY_MS)
    const response = await request

    expect(response.status).toBe('done')
    expect(response.answer).toContain('退货')
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

  it('throws when URL ingestion has no backend', async () => {
    await expect(ingestUrl('https://example.com')).rejects.toThrow('后端不可用')
  })

  it('resets the local session without backend errors', async () => {
    await expect(resetSession()).resolves.toBeUndefined()
  })
})
