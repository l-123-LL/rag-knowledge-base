import { useState } from 'react'
import type { Conversation } from '../types'
import { AnswerBody } from './AnswerBody'
import { AlertIcon, ThumbDownIcon, ThumbUpIcon } from './icons'
import { CitationList } from './CitationList'

interface AnswerCardProps {
  conversation: Conversation
  onFeedback?: (rating: 'up' | 'down') => void
}

/** 生成中骨架屏：保留 aria-label，屏幕阅读器仍然读得到"正在生成答案"。 */
function AnswerSkeleton() {
  return (
    <div aria-label="正在生成答案" className="space-y-2.5 pt-1">
      <div className="skeleton-line h-3 w-[86%] rounded bg-slate-200" />
      <div className="skeleton-line h-3 w-[72%] rounded bg-slate-200" />
      <div className="skeleton-line h-3 w-[54%] rounded bg-slate-200" />
    </div>
  )
}

export function AnswerCard({ conversation, onFeedback }: AnswerCardProps) {
  // 记录用户反馈状态，让按钮有明显选中反馈。
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null)
  const isInsufficient = conversation.status === 'insufficient'

  return (
    <article className="animate-fade-in overflow-hidden rounded-card border border-line bg-surface">
      {/* 提问行：浅底 + 发问标签，与回答区形成稳定分隔 */}
      <div className="flex items-start gap-3 border-b border-line bg-mist/60 px-4 py-3 sm:px-5">
        <span className="mt-0.5 inline-flex h-5 shrink-0 items-center rounded border border-line bg-surface px-1.5 text-micro font-semibold text-ink-500">
          问
        </span>
        <h2 className="min-w-0 flex-1 text-body font-medium text-ink-900">
          {conversation.question}
        </h2>
      </div>

      <div className="flex items-start gap-3 px-4 py-4 sm:px-5 sm:py-5">
        <span className="mt-0.5 inline-flex h-5 shrink-0 items-center rounded border border-brand-100 bg-brand-50 px-1.5 text-micro font-semibold text-brand-700">
          答
        </span>

        <div className="min-w-0 flex-1">
          {conversation.status === 'loading' ? (
            <AnswerSkeleton />
          ) : isInsufficient ? (
            // 无资料时明确提示，而不是强行给出不确定答案。
            <div className="rounded-card border border-amber-200/70 bg-amber-50/70 px-4 py-3.5">
              <div className="flex items-center gap-2">
                <AlertIcon className="h-4 w-4 shrink-0 text-amber-600" />
                <p className="text-ui font-semibold text-amber-900">资料不足</p>
                <span className="chip border-amber-200/70 bg-white/70 text-amber-700">
                  已转人工
                </span>
              </div>
              <div className="mt-2 text-ui text-amber-900/90">
                <AnswerBody text={conversation.answer ?? ''} />
              </div>
            </div>
          ) : (
            <>
              <AnswerBody text={conversation.answer ?? ''} />
              <CitationList citations={conversation.citations} />

              {onFeedback ? (
                <div className="mt-4 flex items-center gap-2 border-t border-line pt-3.5">
                  <span className="mr-1 text-caption text-ink-500">
                    这个回答有帮助吗？
                  </span>
                  <button
                    type="button"
                    aria-pressed={feedback === 'up'}
                    onClick={() => {
                      setFeedback('up')
                      onFeedback('up')
                    }}
                    className={`inline-flex items-center gap-1.5 rounded-control border px-2.5 py-1 text-caption font-medium transition-colors ${
                      feedback === 'up'
                        ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                        : 'border-line text-ink-500 hover:border-emerald-200 hover:text-emerald-700'
                    }`}
                  >
                    <ThumbUpIcon className="h-3.5 w-3.5" />
                    有帮助
                  </button>
                  <button
                    type="button"
                    aria-pressed={feedback === 'down'}
                    onClick={() => {
                      setFeedback('down')
                      onFeedback('down')
                    }}
                    className={`inline-flex items-center gap-1.5 rounded-control border px-2.5 py-1 text-caption font-medium transition-colors ${
                      feedback === 'down'
                        ? 'border-rose-200 bg-rose-50 text-rose-700'
                        : 'border-line text-ink-500 hover:border-rose-200 hover:text-rose-700'
                    }`}
                  >
                    <ThumbDownIcon className="h-3.5 w-3.5" />
                    没帮助
                  </button>
                </div>
              ) : null}
            </>
          )}
        </div>
      </div>
    </article>
  )
}
