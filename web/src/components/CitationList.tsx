import { useState } from 'react'
import type { Citation } from '../types'
import { ChevronDownIcon, LinkIcon } from './icons'

interface CitationListProps {
  citations: Citation[]
}

export function CitationList({ citations }: CitationListProps) {
  // 默认展开第一条引用，点击后切换展开/收起。
  const [openId, setOpenId] = useState<string | null>(citations[0]?.id ?? null)

  if (citations.length === 0) {
    return null
  }

  return (
    <div className="mt-4 border-t border-line pt-4">
      <div className="mb-2 text-xs font-medium text-ink-500">引用来源</div>
      <div className="space-y-2">
        {citations.map((citation) => {
          const isOpen = openId === citation.id

          return (
            <div
              key={citation.id}
              className="overflow-hidden rounded-lg border border-line bg-white"
            >
              <button
                type="button"
                onClick={() =>
                  setOpenId((current) =>
                    current === citation.id ? null : citation.id,
                  )
                }
                className="flex w-full items-center justify-between gap-3 px-3.5 py-3 text-left"
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-ink-900">
                    {citation.title}
                  </span>
                  <span className="mt-1 block text-xs text-ink-500">
                    {citation.location}
                  </span>
                </span>
                <ChevronDownIcon
                  className={`h-4 w-4 shrink-0 text-ink-500 transition-transform ${
                    isOpen ? 'rotate-180' : ''
                  }`}
                />
              </button>

              {isOpen ? (
                <div className="border-t border-line bg-mist px-3.5 py-3">
                  <p className="text-sm leading-6 text-ink-600">
                    {citation.snippet}
                  </p>
                  <a
                    href={citation.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700"
                  >
                    <LinkIcon className="h-4 w-4" />
                    打开来源
                  </a>
                </div>
              ) : null}
            </div>
          )
        })}
      </div>
    </div>
  )
}
