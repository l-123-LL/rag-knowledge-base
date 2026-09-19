import { useState } from 'react'
import type { Citation } from '../types'
import { ChevronDownIcon, FileIcon, LinkIcon } from './icons'

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
    <section className="mt-4">
      <div className="mb-2 flex items-center gap-2">
        <span className="t-section">引用来源</span>
        <span className="t-num text-micro text-ink-400">{citations.length}</span>
      </div>

      {/* 用列表 + 左侧竖线表达"这些都是同一条回答的依据"，比一叠卡片更紧凑 */}
      <ul className="divide-y divide-line overflow-hidden rounded-card border border-line bg-surface">
        {citations.map((citation) => {
          const isOpen = openId === citation.id

          return (
            <li key={citation.id}>
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() =>
                  setOpenId((current) =>
                    current === citation.id ? null : citation.id,
                  )
                }
                className="flex w-full items-center gap-3 px-3.5 py-2.5 text-left transition-colors hover:bg-mist"
              >
                <FileIcon className="h-4 w-4 shrink-0 text-ink-400" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-ui font-medium text-ink-900">
                    {citation.title}
                  </span>
                  {citation.location ? (
                    <span className="mt-0.5 block truncate text-micro text-ink-500">
                      {citation.location}
                    </span>
                  ) : null}
                </span>
                <ChevronDownIcon
                  className={`h-4 w-4 shrink-0 text-ink-400 transition-transform ${
                    isOpen ? 'rotate-180' : ''
                  }`}
                />
              </button>

              {isOpen ? (
                <div className="border-t border-line bg-mist/60 px-3.5 py-3">
                  <p className="text-caption leading-6 text-ink-600">
                    {citation.snippet}
                  </p>
                  <div className="mt-2.5 flex items-center gap-3">
                    <a
                      href={citation.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-1.5 text-micro font-medium text-brand-600 hover:text-brand-700"
                    >
                      <LinkIcon className="h-3.5 w-3.5" />
                      打开来源
                    </a>
                    {typeof citation.score === 'number' ? (
                      <span className="t-num text-micro text-ink-400">
                        相关度 {citation.score.toFixed(2)}
                      </span>
                    ) : null}
                  </div>
                </div>
              ) : null}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
