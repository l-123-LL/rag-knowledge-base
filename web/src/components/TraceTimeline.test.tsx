import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TraceTimeline } from './TraceTimeline'
import type { TraceRecord } from '../types'

const trace: TraceRecord = {
  trace_id: 'tr_test',
  tenant_id: 'default',
  question: '订单 SO20260901001 现在什么状态',
  mode: 'tools',
  model: 'order_lookup',
  steps: [
    { step: 1, action: 'intent', intent: 'knowledge' },
    {
      step: 2,
      action: 'tool',
      tool: 'order_lookup',
      status: 'ok',
      code: 'OK',
      attempts: 2,
      duration_ms: 3,
      input_summary: 'SO20260901001',
    },
  ],
  tool_calls: 1,
  citation_count: 1,
  latency_ms: 12,
  usage: { total_tokens: 0 },
  cost: null,
}

describe('TraceTimeline', () => {
  it('renders steps with tool, retry and cost information', () => {
    render(<TraceTimeline trace={trace} />)

    expect(screen.getByText('执行轨迹')).toBeInTheDocument()
    // 模型名与步骤详情里都会出现 order_lookup，这里只确认它被渲染出来。
    expect(screen.getAllByText(/order_lookup/).length).toBeGreaterThan(0)
    expect(screen.getByText(/重试1次/)).toBeInTheDocument()
    expect(screen.getByText(/未配置单价/)).toBeInTheDocument()
  })

  it('shows an empty hint when there is no trace', () => {
    render(<TraceTimeline trace={null} />)

    expect(screen.getByText(/本次没有产生轨迹/)).toBeInTheDocument()
  })
})
