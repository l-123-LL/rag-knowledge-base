import { useState, type FormEvent } from 'react'
import { HumanAgentIcon, SendIcon } from './icons'

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
  const [focused, setFocused] = useState(false)
  const canSend = Boolean(value.trim()) && !disabled

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
      className="border-t border-line bg-surface px-4 py-3.5 lg:px-8"
    >
      <div className="mx-auto max-w-3xl">
        {/* 输入区整体作为焦点容器：聚焦时整块描边变成主色，比单个 textarea 更清晰 */}
        <div
          className={`flex items-end gap-2 rounded-panel border bg-surface p-1.5 transition-colors ${
            focused ? 'border-brand-300 shadow-composer' : 'border-line'
          }`}
        >
          <label htmlFor="question" className="sr-only">
            输入客服问题
          </label>
          <textarea
            id="question"
            value={value}
            onChange={(event) => setValue(event.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                submitQuestion()
              }
            }}
            placeholder="输入客服问题，例如：如何申请退货？"
            rows={2}
            className="max-h-40 min-h-[48px] flex-1 resize-none border-0 bg-transparent px-2.5 py-2 text-body text-ink-900 outline-none placeholder:text-ink-400 focus-visible:outline-none"
          />

          <div className="mb-0.5 flex shrink-0 items-center gap-1.5">
            {onTransfer ? (
              // 一键转人工：走同一条问答链路，由后端意图路由建单并返回工单号。
              <button
                type="button"
                onClick={onTransfer}
                disabled={disabled}
                title="直接转人工客服"
                className="inline-flex h-9 items-center gap-1.5 rounded-control border border-line bg-surface px-2.5 text-caption font-medium text-ink-600 transition-colors hover:border-brand-200 hover:text-brand-700 disabled:cursor-not-allowed disabled:text-ink-400"
              >
                <HumanAgentIcon className="h-4 w-4" />
                转人工
              </button>
            ) : null}
            <button
              type="submit"
              disabled={!canSend}
              className="inline-flex h-9 w-9 items-center justify-center rounded-control bg-ink-950 text-white transition-colors hover:bg-ink-900 disabled:cursor-not-allowed disabled:bg-slate-300"
              aria-label="发送问题"
            >
              <SendIcon className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="mt-1.5 flex items-center justify-between px-1">
          <p className="text-micro text-ink-400">
            Enter 发送，Shift + Enter 换行
          </p>
          <p className="hidden text-micro text-ink-400 sm:block">
            回答优先命中 FAQ，其次检索知识库并附引用
          </p>
        </div>
      </div>
    </form>
  )
}
