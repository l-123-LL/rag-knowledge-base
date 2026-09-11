import { useState } from 'react'
import type { Source } from '../types'
import { AlertIcon, CheckIcon, ChevronDownIcon, LinkIcon } from './icons'

interface SourcePanelProps {
  sources: Source[]
}

const statusMeta = {
  indexed: { label: '已索引', className: 'bg-emerald-50 text-emerald-700' },
  pending: { label: '待处理', className: 'bg-amber-50 text-amber-700' },
  failed: { label: '失败', className: 'bg-rose-50 text-rose-700' },
} as const

export function SourcePanel({ sources }: SourcePanelProps) {
  // 当前选中的来源，用于展开或收起详情。
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = sources.find((source) => source.id === selectedId) ?? null

  return (
    <aside className="flex h-full min-h-0 flex-col bg-surface lg:border-r lg:border-line">
      <div className="border-b border-line px-5 py-5">
        <div className="mb-2 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-ink-900">知识来源</h2>
            <p className="mt-1 text-xs text-ink-500">示例资料列表</p>
          </div>
          <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-600">
            {sources.length} 条
          </span>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        <div className="space-y-2">
          {sources.map((source) => {
            const status = statusMeta[source.status]
            const isSelected = source.id === selectedId

            return (
              <button
                key={source.id}
                type="button"
                onClick={() =>
                  setSelectedId((current) =>
                    current === source.id ? null : source.id,
                  )
                }
                className={`w-full rounded-card border px-3.5 py-3 text-left transition ${
                  isSelected
                    ? 'border-brand-500 bg-brand-50'
                    : 'border-line bg-white hover:border-slate-300 hover:bg-slate-50'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink-900">
                      {source.title}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span className="text-xs text-ink-500">
                        {source.category}
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${status.className}`}
                      >
                        {status.label}
                      </span>
                    </div>
                  </div>
                  <ChevronDownIcon
                    className={`mt-0.5 h-4 w-4 shrink-0 text-ink-500 transition-transform ${
                      isSelected ? 'rotate-180' : ''
                    }`}
                  />
                </div>

                {isSelected ? (
                  <div className="mt-3 border-t border-brand-100 pt-3">
                    <p className="text-sm leading-6 text-ink-600">
                      {source.description}
                    </p>
                    <div className="mt-3 flex items-center gap-2 text-xs text-ink-500">
                      <span>更新：{source.updatedAt}</span>
                      {source.status === 'indexed' ? (
                        <CheckIcon className="h-4 w-4 text-emerald-600" />
                      ) : source.status === 'failed' ? (
                        <AlertIcon className="h-4 w-4 text-rose-500" />
                      ) : null}
                    </div>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700"
                    >
                      <LinkIcon className="h-4 w-4" />
                      查看来源
                    </a>
                  </div>
                ) : null}
              </button>
            )
          })}
        </div>
      </div>

      <div className="border-t border-line px-5 py-4">
        <div className="flex items-start gap-2 text-xs leading-5 text-ink-500">
          <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
          <span>当前为纯前端预览，数据为本地模拟内容。</span>
        </div>
      </div>
    </aside>
  )
}
