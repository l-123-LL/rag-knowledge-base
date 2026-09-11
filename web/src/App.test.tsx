import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

describe('App', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows the simulated error state', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: '模拟错误状态' }))

    expect(
      screen.getByText('接口暂时不可用，请稍后重试。'),
    ).toBeInTheDocument()
  })

  it('returns a sample answer and citation for a matching question', () => {
    vi.useFakeTimers()
    render(<App />)

    const input = screen.getByLabelText('输入医学问题')
    fireEvent.change(input, {
      target: { value: '成人流感的抗病毒治疗时机是什么？' },
    })
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' })

    expect(screen.getByLabelText('正在生成答案')).toBeInTheDocument()

    act(() => {
      vi.advanceTimersByTime(650)
    })

    expect(
      screen.getByText(/轻症且无高危因素者可在医生评估后决定是否用药/),
    ).toBeInTheDocument()
    expect(
      screen.getAllByText('流行性感冒诊疗方案（2025年版）').length,
    ).toBeGreaterThan(0)
  })

  it('returns the insufficient-data state for unmatched questions', () => {
    vi.useFakeTimers()
    render(<App />)

    const input = screen.getByLabelText('输入医学问题')
    fireEvent.change(input, { target: { value: '今天天气如何' } })
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' })

    act(() => {
      vi.advanceTimersByTime(650)
    })

    expect(screen.getByText('示例资料不足')).toBeInTheDocument()
  })
})
