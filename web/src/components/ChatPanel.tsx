import { useMemo } from 'react'
import type { Conversation, MockConversation } from '../types'
import { SparkIcon } from './icons'
import { AnswerCard } from './AnswerCard'
import { QuestionInput } from './QuestionInput'

interface ChatPanelProps {
  conversations: Conversation[]
  error: string | null
  isLoading: boolean
  mockQuestions: MockConversation[]
  onAsk: (question: string) => void
  onTransfer?: () => void
  onNewSession?: () => void
  onFeedback?: (question: string, rating: 'up' | 'down') => void
}

function EmptyState({
  suggestions,
  onAsk,
}: {
  suggestions: MockConversation[]
  onAsk: (question: string) => void
}) {
  return (
    <div className="flex min-h-full items-center justify-center px-6 py-12">
      <div className="w-full max-w-xl">
        <div className="flex h-9 w-9 items-center justify-center rounded-card border border-line bg-surface text-ink-700">
          <SparkIcon className="h-4.5 w-4.5" />
        </div>
        <h2 className="mt-4 text-display font-semibold text-ink-950">
          今天需要帮客户解决什么？
        </h2>
        <p className="mt-2 text-body text-ink-500">
          回答优先命中 FAQ；没有标准答案时检索知识库并附引用来源，资料不足会自动转人工。
        </p>

        <div className="mt-6 space-y-1.5">
          {suggestions.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onAsk(item.question)}
              className="flex w-full items-center justify-between gap-3 rounded-card border border-line bg-surface px-3.5 py-2.5 text-left text-ui text-ink-700 transition-colors hover:border-brand-200 hover:bg-brand-50/40 hover:text-brand-700"
            >
              <span className="truncate">{item.question}</span>
              {/* 装饰性提示：从无障碍名里隐藏，保证按钮名就是问题本身 */}
              <span aria-hidden="true" className="shrink-0 text-micro text-ink-400">
                试试
              </span>
            </button>
          ))}
          <button
            type="button"
            onClick={() => onAsk('模拟错误')}
            className="flex w-full items-center justify-between gap-3 rounded-card border border-dashed border-line px-3.5 py-2.5 text-left text-ui text-ink-500 transition-colors hover:border-rose-200 hover:text-rose-700"
          >
            <span>模拟错误状态</span>
            <span aria-hidden="true" className="shrink-0 text-micro text-ink-400">
              演示容错
            </span>
          </button>
        </div>
      </div>
    </div>
  )
}

export function ChatPanel({
  conversations,
  error,
  isLoading,
  mockQuestions,
  onAsk,
  onTransfer,
  onNewSession,
  onFeedback,
}: ChatPanelProps) {
  // 首屏没有对话时展示引导，避免用户面对空白页面。
  const showEmptyState = useMemo(
    () => conversations.length === 0 && !error,
    [conversations.length, error],
  )

  return (
    <section className="flex h-full min-h-0 flex-col bg-canvas">
      <div className="border-b border-line bg-surface px-4 py-3 lg:px-8">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4">
          <div className="min-w-0">
            <h1 className="truncate text-ui font-semibold text-ink-950">
              智能问答工作台
            </h1>
            <p className="mt-0.5 truncate text-micro text-ink-500">
              知识库检索 · 引用可核对 · 资料不足自动转人工
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            {onNewSession ? (
              <button type="button" onClick={onNewSession} className="btn-secondary">
                新会话
              </button>
            ) : null}
          </div>
        </div>
      </div>

      {error ? (
        <div className="mx-auto mt-4 w-full max-w-3xl px-4 lg:px-8">
          <div
            role="alert"
            className="rounded-card border border-rose-200/70 bg-rose-50 px-3.5 py-2.5 text-ui text-rose-700"
          >
            {error}
          </div>
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {showEmptyState ? (
          <EmptyState suggestions={mockQuestions} onAsk={onAsk} />
        ) : (
          <div
            aria-live="polite"
            className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-5 lg:px-8"
          >
            {conversations.map((conversation) => (
              <AnswerCard
                key={conversation.id}
                conversation={conversation}
                onFeedback={
                  onFeedback
                    ? (rating) => onFeedback(conversation.question, rating)
                    : undefined
                }
              />
            ))}
          </div>
        )}
      </div>

      <QuestionInput
        disabled={isLoading}
        onAsk={onAsk}
        onTransfer={onTransfer}
      />
    </section>
  )
}
