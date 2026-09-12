import { useState } from 'react'
import type { Conversation } from '../types'
import { AlertIcon } from './icons'
import { CitationList } from './CitationList'

interface AnswerCardProps {
  conversation: Conversation
  onFeedback?: (rating: 'up' | 'down') => void
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-1" aria-label="正在生成答案">
      <span className="h-2 w-2 animate-bounce rounded-full bg-brand-500 [animation-delay:0ms]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-brand-500 [animation-delay:120ms]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-brand-500 [animation-delay:240ms]" />
    </div>
  )
}

export function AnswerCard({ conversation, onFeedback }: AnswerCardProps) {
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null)
  const isInsufficient = conversation.status === 'insufficient'

  return (
    <article className="animate-fade-in overflow-hidden rounded-2xl border border-line bg-surface shadow-panel">
      <div className="flex gap-3 border-b border-line/80 px-5 py-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-ink-950 text-xs font-semibold text-white">
          问
        </div>
        <p className="pt-1 text-sm font-medium leading-6 text-ink-900">
          {conversation.question}
        </p>
      </div>

      <div className="flex gap-3 px-5 py-5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-600 text-xs font-semibold text-white">
          答
        </div>
        <div className="min-w-0 flex-1">
          {conversation.status === 'loading' ? (
            <TypingIndicator />
          ) : isInsufficient ? (
            <div className="flex items-start gap-3 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3">
              <AlertIcon className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
              <div>
                <p className="text-sm font-medium text-amber-900">
                  资料不足
                </p>
                <p className="mt-1 text-sm leading-6 text-amber-800">
                  {conversation.answer}
                </p>
              </div>
            </div>
          ) : (
            <>
              <p className="whitespace-pre-wrap text-[15px] leading-8 text-ink-700">
                {conversation.answer}
              </p>
              <CitationList citations={conversation.citations} />
              {onFeedback ? (
                <div className="mt-5 flex items-center gap-4 border-t border-line pt-4">
                  <span className="text-xs text-ink-500">
                    这个回答有帮助吗？
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setFeedback('up')
                      onFeedback('up')
                    }}
                    className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                      feedback === 'up'
                        ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
                        : 'border-line text-ink-500 hover:border-emerald-200 hover:text-emerald-700'
                    }`}
                  >
                    有帮助
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setFeedback('down')
                      onFeedback('down')
                    }}
                    className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                      feedback === 'down'
                        ? 'border-rose-200 bg-rose-50 text-rose-700'
                        : 'border-line text-ink-500 hover:border-rose-200 hover:text-rose-700'
                    }`}
                  >
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
