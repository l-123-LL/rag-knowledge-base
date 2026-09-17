import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App, { readTraceId } from './App'
import { MOCK_DELAY_MS } from './api/client'

describe('App', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows the simulated error state', async () => {
    render(<App />)
    await act(async () => {})

    fireEvent.click(screen.getByRole('button', { name: '模拟错误状态' }))

    expect(
      screen.getByText('接口暂时不可用，请稍后重试。'),
    ).toBeInTheDocument()
  })

  it('hides admin management tools from normal users', async () => {
    vi.stubEnv('VITE_ADMIN_API_KEY', '')
    render(<App />)
    await act(async () => {})

    expect(screen.queryAllByText('新增 FAQ')).toHaveLength(0)
    expect(screen.queryAllByText('导入网页')).toHaveLength(0)
    expect(screen.queryAllByText('上传资料')).toHaveLength(0)
    vi.unstubAllEnvs()
  })

  it('returns a sample answer and citation for a matching question', async () => {
    vi.useFakeTimers()
    render(<App />)
    await act(async () => {})

    const input = screen.getByLabelText('输入客服问题')
    fireEvent.change(input, {
      target: { value: '如何申请退货？' },
    })
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' })

    expect(screen.getByLabelText('正在生成答案')).toBeInTheDocument()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(MOCK_DELAY_MS)
    })

    expect(
      screen.getByText(/根据示例资料，收到商品后 7 天内可申请无理由退货/),
    ).toBeInTheDocument()
    expect(
      screen.getAllByText('退换货政策说明').length,
    ).toBeGreaterThan(0)
  })

  it('returns the insufficient-data state for unmatched questions', async () => {
    vi.useFakeTimers()
    render(<App />)
    await act(async () => {})

    const input = screen.getByLabelText('输入客服问题')
    fireEvent.change(input, { target: { value: '今天天气如何' } })
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' })

    await act(async () => {
      await vi.advanceTimersByTimeAsync(MOCK_DELAY_MS)
    })

    expect(screen.getByText('资料不足')).toBeInTheDocument()
  })

  it('offers one-click transfer to a human agent', async () => {
    vi.useFakeTimers()
    render(<App />)
    await act(async () => {})

    // 输入框旁边必须有明确的转人工入口，用户不需要自己想办法。
    fireEvent.click(screen.getByRole('button', { name: '转人工' }))

    expect(screen.getByText('我要转人工客服')).toBeInTheDocument()

    await act(async () => {
      await vi.advanceTimersByTimeAsync(MOCK_DELAY_MS)
    })
  })

  it('reads a shared trace id from the url', () => {
    expect(readTraceId('?trace=tr_abc123')).toBe('tr_abc123')
    expect(readTraceId('?trace=%20')).toBeNull()
    expect(readTraceId('')).toBeNull()
  })
})
