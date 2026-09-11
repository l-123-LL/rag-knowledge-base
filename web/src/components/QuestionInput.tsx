import { useState, type FormEvent } from 'react'
import { SendIcon } from './icons'

interface QuestionInputProps {
  disabled?: boolean
  onAsk: (question: string) => void
}

export function QuestionInput({ disabled, onAsk }: QuestionInputProps) {
  const [value, setValue] = useState('')

  // 统一处理点击发送和键盘 Enter 发送。
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
      className="border-t border-line bg-surface px-4 py-4 lg:px-6"
    >
      <div className="mx-auto flex max-w-3xl items-end gap-3">
        <label htmlFor="question" className="sr-only">
          输入医学问题
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
          placeholder="输入医学问题，例如：成人流感的抗病毒治疗时机是什么？"
          rows={2}
          className="max-h-36 min-h-[52px] flex-1 resize-none rounded-xl border border-line bg-white px-4 py-3 text-sm leading-6 text-ink-900 outline-none transition placeholder:text-ink-500 focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="inline-flex h-[52px] w-[52px] shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          aria-label="发送问题"
        >
          <SendIcon className="h-5 w-5" />
        </button>
      </div>
    </form>
  )
}
