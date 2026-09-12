import { useMemo } from 'react'
import type { Conversation, MockConversation } from '../types'
import { AnswerCard } from './AnswerCard'
import { QuestionInput } from './QuestionInput'

interface ChatPanelProps {
  conversations: Conversation[]
  error: string | null
  isLoading: boolean
  mockQuestions: MockConversation[]
  onAsk: (question: string) => void
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
    <div className="flex min-h-full items-center justify-center px-6 py-14">
      <div className="w-full max-w-2xl text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-ink-950 text-white shadow-panel">
          <svg
            viewBox="0 0 24 24"
            className="h-6 w-6"
            fill="none"
            aria-hidden="true"
          >
            <path
              d="M8.5 9.5h7M8.5 12.5h4M12 21a9 9 0 1 0-9-9v4a2 2 0 0 0 2 2h3a4 4 0 0 0 4-4Z"
              stroke="currentColor"
              strokeWidth="1.7"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <h2 className="mt-6 text-3xl font-semibold tracking-tight text-ink-950">
          企业智能客服
        </h2>
        <p className="mx-auto mt-3 max-w-lg text-sm leading-6 text-ink-500">
          基于企业知识库的实时问答，支持 FAQ 优先命中、RAG 检索、引用来源和转人工工单。
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-2">
          {suggestions.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onAsk(item.question)}
              className="rounded-full border border-line bg-white px-4 py-2 text-sm text-ink-600 shadow-sm transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700"
            >
              {item.question}
            </button>
          ))}
          <button
            type="button"
            onClick={() => onAsk('模拟错误')}
            className="rounded-full border border-line bg-white px-4 py-2 text-sm text-ink-600 transition hover:border-rose-200 hover:bg-rose-50 hover:text-rose-700"
          >
            模拟错误状态
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
  onNewSession,
  onFeedback,
}: ChatPanelProps) {
  const showEmptyState = useMemo(
    () => conversations.length === 0 && !error,
    [conversations.length, error],
  )

  return (
    <section className="flex h-full min-h-0 flex-col bg-canvas">
      <div className="border-b border-line bg-surface/90 px-5 py-4 backdrop-blur lg:px-8">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <div>
            <h1 className="text-base font-semibold tracking-tight text-ink-950">
              智能问答工作台
            </h1>
            <p className="mt-1 text-xs text-ink-500">
              基于企业知识库的实时回答
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="hidden items-center gap-2 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 sm:flex">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              流式输出
            </span>
            {onNewSession ? (
              <button
                type="button"
                onClick={onNewSession}
                className="rounded-lg border border-line bg-white px-3 py-1.5 text-xs font-medium text-ink-600 transition hover:border-brand-200 hover:text-brand-700"
              >
                新会话
              </button>
            ) : null}
          </div>
        </div>
      </div>

      {error ? (
        <div className="mx-auto mt-5 w-full max-w-5xl px-5 lg:px-8">
          <div className="rounded-xl border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {showEmptyState ? (
          <EmptyState suggestions={mockQuestions} onAsk={onAsk} />
        ) : (
          <div className="mx-auto flex max-w-5xl flex-col gap-5 px-4 py-6 lg:px-8">
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

      <QuestionInput disabled={isLoading} onAsk={onAsk} />
    </section>
  )
}
