import { useState, type FormEvent } from 'react'
import { SendIcon } from './icons'

interface QuestionInputProps {
  disabled?: boolean
  onAsk: (question: string) => void
  onTransfer?: () => void
}

export function QuestionInput({
  disabled,
  onAsk,
  onTransfer,
}: QuestionInputProps) {
  const [value, setValue] = useState('')

  // 点击按钮和 Enter 都走同一个提交逻辑。
  function submitQuestion() {
    const question = value.trim()

    if (!question || disabled) {
      return
    }

    onAsk(question)
    setValue('')
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    submitQuestion()
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t border-line bg-surface/95 px-4 py-4 backdrop-blur lg:px-8"
    >
      <div className="mx-auto max-w-5xl">
        <div className="flex items-end gap-3 rounded-2xl border border-line bg-surface p-2 shadow-composer">
          <label htmlFor="question" className="sr-only">
            输入客服问题
          </label>
          <textarea
            id="question"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                submitQuestion()
              }
            }}
            placeholder="输入客服问题，例如：如何申请退货？"
            rows={2}
            className="max-h-40 min-h-[52px] flex-1 resize-none border-0 bg-transparent px-3 py-2.5 text-sm leading-6 text-ink-900 outline-none placeholder:text-ink-400"
          />
          {onTransfer ? (
            // 一键转人工：走同一条问答链路，由后端意图路由建单并返回工单号。
            <button
              type="button"
              onClick={onTransfer}
              disabled={disabled}
              className="mb-0.5 inline-flex h-11 shrink-0 items-center rounded-xl border border-line bg-white px-3.5 text-xs font-medium text-ink-600 transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700 disabled:cursor-not-allowed disabled:border-line disabled:bg-white disabled:text-slate-300"
            >
              转人工
            </button>
          ) : null}
          <button
            type="submit"
            disabled={disabled || !value.trim()}
            className="mb-0.5 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-ink-950 text-white transition hover:bg-ink-900 disabled:cursor-not-allowed disabled:bg-slate-300"
            aria-label="发送问题"
          >
            <SendIcon className="h-5 w-5" />
          </button>
        </div>
        <p className="mt-2 px-2 text-[11px] text-ink-400">
          Enter 发送，Shift + Enter 换行。回答会优先使用 FAQ，再走知识库检索。
        </p>
      </div>
    </form>
  )
}
