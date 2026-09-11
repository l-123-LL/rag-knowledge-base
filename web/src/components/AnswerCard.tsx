import type { Conversation } from '../types'
import { AlertIcon } from './icons'
import { CitationList } from './CitationList'

interface AnswerCardProps {
  conversation: Conversation
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

export function AnswerCard({ conversation }: AnswerCardProps) {
  // 没有命中示例资料时展示“资料不足”，而不是生成不确定答案。
  const isInsufficient = conversation.status === 'insufficient'

  return (
    <article className="animate-fade-in rounded-card border border-line bg-surface p-5 shadow-soft">
      <div className="rounded-lg bg-mist px-4 py-3">
        <p className="text-sm font-medium text-ink-900">
          {conversation.question}
        </p>
      </div>

      <div className="mt-4">
        {conversation.status === 'loading' ? (
          <TypingIndicator />
        ) : isInsufficient ? (
          <div className="flex items-start gap-3 rounded-lg border border-amber-100 bg-amber-50 px-4 py-3">
            <AlertIcon className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
            <div>
              <p className="text-sm font-medium text-amber-900">示例资料不足</p>
              <p className="mt-1 text-sm leading-6 text-amber-800">
                {conversation.answer}
              </p>
            </div>
          </div>
        ) : (
          <>
            <p className="whitespace-pre-wrap text-sm leading-7 text-ink-600">
              {conversation.answer}
            </p>
            <CitationList citations={conversation.citations} />
          </>
        )}
      </div>
    </article>
  )
}
