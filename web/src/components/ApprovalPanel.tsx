import { useState } from 'react'
import type { ApprovalRecord } from '../types'

interface ApprovalPanelProps {
  approvals: ApprovalRecord[]
  error?: string | null
  onDecide: (approvalId: string, approved: boolean, comment?: string) => void
}

const STATUS_LABEL: Record<string, string> = {
  pending: '待审批',
  executed: '已执行',
  rejected: '已驳回',
  failed: '执行失败',
  approved: '已批准',
}

const STATUS_STYLE: Record<string, string> = {
  pending: 'border-amber-200/70 bg-amber-50 text-amber-700',
  executed: 'border-emerald-200/70 bg-emerald-50 text-emerald-700',
  rejected: 'border-line bg-mist text-ink-500',
  failed: 'border-rose-200/70 bg-rose-50 text-rose-700',
  approved: 'border-brand-100 bg-brand-50 text-brand-700',
}

export function ApprovalPanel({ approvals, error, onDecide }: ApprovalPanelProps) {
  // 驳回理由是可选项：填了就随审批决定一起记入审计记录。
  const [comment, setComment] = useState('')
  const pending = approvals.filter((item) => item.status === 'pending')
  const decided = approvals.filter((item) => item.status !== 'pending').slice(0, 3)

  return (
    <section className="border-t border-line px-4 py-3.5">
      <div className="flex items-center justify-between">
        <p className="t-section">高风险操作审批</p>
        <span className="t-num text-micro text-ink-500">
          待处理 {pending.length}
        </span>
      </div>
      <p className="mt-1.5 text-micro leading-5 text-ink-500">
        退款等写操作不会自动执行，批准后才落地（本地 mock，不涉及真实资金）
      </p>

      {error ? (
        <p className="mt-2.5 rounded-control border border-rose-200/70 bg-rose-50 px-2.5 py-2 text-micro text-rose-700">
          {error}
        </p>
      ) : null}

      {pending.length > 0 ? (
        <label className="mt-2.5 block">
          <span className="text-micro text-ink-500">
            驳回理由（可选，会记入审批记录）
          </span>
          <input
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder="例如：金额超出免审额度"
            className="mt-1 w-full rounded-control border border-line bg-surface px-2.5 py-1.5 text-caption text-ink-900 outline-none placeholder:text-ink-400 focus:border-brand-300"
          />
        </label>
      ) : null}

      {pending.length === 0 && decided.length === 0 ? (
        <p className="mt-2.5 text-micro text-ink-400">当前没有需要审批的操作。</p>
      ) : null}

      <ul className="mt-2.5 space-y-2">
        {pending.map((item) => (
          <li key={item.id} className="rounded-card border border-line bg-surface px-3 py-2.5">
            <div className="flex items-center justify-between">
              <span className="text-caption font-medium text-ink-900">
                {item.tool}
              </span>
              <span className="chip border-amber-200/70 bg-amber-50 text-amber-700">
                {STATUS_LABEL[item.status] ?? item.status}
              </span>
            </div>
            <p className="t-num mt-1 text-micro text-ink-500">
              审批号 {item.id}
              {item.preview?.amount ? ` · 金额 ${item.preview.amount} 元` : ''}
              {item.preview?.order_status ? ` · 订单 ${item.preview.order_status}` : ''}
            </p>
            <div className="mt-2.5 flex gap-1.5">
              <button
                type="button"
                onClick={() => onDecide(item.id, true, comment || undefined)}
                className="btn-primary"
              >
                批准并执行
              </button>
              <button
                type="button"
                onClick={() => onDecide(item.id, false, comment || undefined)}
                className="btn-secondary hover:border-rose-200 hover:text-rose-700"
              >
                驳回
              </button>
            </div>
          </li>
        ))}
      </ul>

      {decided.length > 0 ? (
        <ul className="mt-2.5 space-y-1">
          {decided.map((item) => (
            <li
              key={item.id}
              className={`flex items-center justify-between rounded-control border px-2.5 py-1.5 text-micro ${
                STATUS_STYLE[item.status] ?? 'border-line bg-mist text-ink-500'
              }`}
            >
              <span>{item.tool}</span>
              <span>{STATUS_LABEL[item.status] ?? item.status}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  )
}
