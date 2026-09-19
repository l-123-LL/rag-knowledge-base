import type { TraceRecord, TraceStep } from '../types'

interface TraceTimelineProps {
  trace: TraceRecord | null
  onClose?: () => void
}

const ACTION_LABEL: Record<string, string> = {
  intent: '意图路由',
  faq: 'FAQ 命中',
  tool: '工具调用',
  fallback: '降级',
}

function statusTone(step: TraceStep) {
  if (step.action === 'tool' && step.status && step.status !== 'ok') {
    return 'border-rose-100 bg-rose-50 text-rose-700'
  }
  if (step.action === 'fallback') {
    return 'border-amber-100 bg-amber-50 text-amber-700'
  }
  return 'border-line bg-white text-ink-600'
}

function describe(step: TraceStep) {
  const parts: string[] = []
  if (step.tool) parts.push(step.tool)
  if (step.intent) parts.push(step.intent)
  if (step.matched) parts.push(step.matched)
  if (step.input_summary) parts.push(step.input_summary)
  if (step.reason) parts.push(step.reason)
  return parts.join(' · ')
}

export function TraceTimeline({ trace, onClose }: TraceTimelineProps) {
  return (
    <section className="mx-auto max-w-3xl px-4 py-5 lg:px-8">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-ui font-semibold text-ink-950">执行轨迹</h2>
          <p className="mt-0.5 text-micro text-ink-500">
            {trace
              ? `trace ${trace.trace_id} · 模式 ${trace.mode ?? 'rag'} · 模型 ${trace.model ?? '-'}`
              : '本次没有产生轨迹（RAG 模式或后端不可用）'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {onClose ? (
            <button type="button" onClick={onClose} className="btn-secondary">
              收起
            </button>
          ) : null}
        </div>
      </div>

      {trace ? (
        <>
          <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <div className="rounded-card border border-line bg-surface px-3 py-2.5">
              <p className="text-micro text-ink-400">工具调用</p>
              <p className="t-num mt-0.5 text-body font-semibold text-ink-900">
                {trace.tool_calls ?? 0} 次
              </p>
            </div>
            <div className="rounded-card border border-line bg-surface px-3 py-2.5">
              <p className="text-micro text-ink-400">引用</p>
              <p className="t-num mt-0.5 text-body font-semibold text-ink-900">
                {trace.citation_count ?? 0} 条
              </p>
            </div>
            <div className="rounded-card border border-line bg-surface px-3 py-2.5">
              <p className="text-micro text-ink-400">总延迟</p>
              <p className="t-num mt-0.5 text-body font-semibold text-ink-900">
                {trace.latency_ms ?? 0} ms
              </p>
            </div>
            <div className="rounded-card border border-line bg-surface px-3 py-2.5">
              <p className="text-micro text-ink-400">Token / 成本</p>
              <p className="t-num mt-0.5 text-body font-semibold text-ink-900">
                {trace.usage?.total_tokens ?? 0} /{' '}
                {trace.cost === null || trace.cost === undefined
                  ? '未配置单价'
                  : trace.cost.toFixed(4)}
              </p>
            </div>
          </div>

          {trace.handoff_reason ? (
            <div className="mb-4 rounded-card border border-amber-200/70 bg-amber-50 px-3 py-2 text-caption text-amber-800">
              转人工原因：{trace.handoff_reason}
            </div>
          ) : null}

          <ol className="space-y-1.5">
            {trace.steps.map((step) => (
              <li
                key={`${step.step}-${step.action}`}
                className={`flex items-start gap-3 rounded-card border px-3 py-2 ${statusTone(step)}`}
              >
                <span className="t-num mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-line bg-surface text-micro font-semibold text-ink-600">
                  {step.step}
                </span>
                <div className="min-w-0">
                  <p className="text-caption font-semibold">
                    {ACTION_LABEL[step.action] ?? step.action}
                  </p>
                  {describe(step) ? (
                    <p className="mt-0.5 break-all text-micro text-ink-500">
                      {describe(step)}
                    </p>
                  ) : null}
                </div>
                <span className="t-num ml-auto shrink-0 text-micro text-ink-500">
                  {step.code && step.code !== 'OK' ? step.code : ''}
                  {typeof step.attempts === 'number' && step.attempts > 1
                    ? ` 重试${step.attempts - 1}次`
                    : ''}
                  {typeof step.duration_ms === 'number' ? ` ${step.duration_ms}ms` : ''}
                </span>
              </li>
            ))}
          </ol>
        </>
      ) : null}
    </section>
  )
}
