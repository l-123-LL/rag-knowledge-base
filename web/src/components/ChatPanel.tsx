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
      <div className="w-full max-w-xl text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-50 text-brand-600">
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
        <h2 className="mt-5 text-xl font-semibold text-ink-900">
          医学知识智能问答
        </h2>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-500">
          输入问题查看前端预览效果。回答和引用均为本地示例数据。
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-2">
          {suggestions.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => onAsk(item.question)}
              className="rounded-full border border-line bg-white px-4 py-2 text-sm text-ink-600 transition hover:border-brand-500 hover:bg-brand-50 hover:text-brand-700"
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
}: ChatPanelProps) {
  // 首屏没有对话时展示引导和示例问题。
  const showEmptyState = useMemo(
    () => conversations.length === 0 && !error,
    [conversations.length, error],
  )

  return (
    <section className="flex h-full min-h-0 flex-col bg-mist">
      <div className="border-b border-line bg-surface px-5 py-4 lg:px-6">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <div>
            <h1 className="text-base font-semibold text-ink-900">智能问答</h1>
            <p className="mt-1 text-xs text-ink-500">基于本地示例资料的预览</p>
          </div>
          <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-600">
            前端预览
          </span>
        </div>
      </div>

      {error ? (
        <div className="mx-auto mt-5 w-full max-w-3xl rounded-card border border-rose-100 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto">
        {showEmptyState ? (
          <EmptyState suggestions={mockQuestions} onAsk={onAsk} />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-4 px-4 py-5 lg:px-6">
            {conversations.map((conversation) => (
              <AnswerCard key={conversation.id} conversation={conversation} />
            ))}
          </div>
        )}
      </div>

      <QuestionInput disabled={isLoading} onAsk={onAsk} />
    </section>
  )
}
