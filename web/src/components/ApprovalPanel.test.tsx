import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ApprovalPanel } from './ApprovalPanel'
import type { ApprovalRecord } from '../types'

const pendingApproval: ApprovalRecord = {
  id: 'AP20260919ABC123',
  tool: 'refund_request',
  status: 'pending',
  preview: { amount: 899, order_status: '已发货' },
}

describe('ApprovalPanel', () => {
  it('shows pending approvals with preview details', () => {
    render(<ApprovalPanel approvals={[pendingApproval]} onDecide={() => {}} />)

    expect(screen.getByText('高风险操作审批')).toBeInTheDocument()
    expect(screen.getByText(/AP20260919ABC123/)).toBeInTheDocument()
    expect(screen.getByText(/金额 899 元/)).toBeInTheDocument()
  })

  it('lets the admin approve an operation', () => {
    const onDecide = vi.fn()
    render(<ApprovalPanel approvals={[pendingApproval]} onDecide={onDecide} />)

    fireEvent.click(screen.getByRole('button', { name: '批准并执行' }))

    expect(onDecide).toHaveBeenCalledWith('AP20260919ABC123', true)
  })

  it('shows an empty hint when nothing needs approval', () => {
    render(<ApprovalPanel approvals={[]} onDecide={() => {}} />)

    expect(screen.getByText('当前没有需要审批的操作。')).toBeInTheDocument()
  })
})
