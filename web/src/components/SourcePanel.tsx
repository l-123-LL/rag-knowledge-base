import { useRef, useState, type FormEvent } from 'react'
import type { Metrics, Source, Stats } from '../types'
import { AlertIcon, CheckIcon, ChevronDownIcon, LinkIcon } from './icons'

interface SourcePanelProps {
  sources: Source[]
  onUploadFile?: (file: File) => Promise<void>
  onIngestUrl?: (url: string) => Promise<void>
  onCreateFaq?: (payload: {
    question: string
    answer: string
    keywords: string[]
  }) => Promise<void>
  onToggleSource?: (sourceId: string, archived: boolean) => Promise<void>
  uploadError?: string | null
  stats?: Stats
  metrics?: Metrics
}

const statusMeta = {
  indexed: {
    label: '已索引',
    className: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
  },
  pending: {
    label: '待处理',
    className: 'bg-amber-50 text-amber-700 ring-amber-100',
  },
  failed: {
    label: '失败',
    className: 'bg-rose-50 text-rose-700 ring-rose-100',
  },
} as const

export function SourcePanel({
  sources,
  onUploadFile,
  onIngestUrl,
  onCreateFaq,
  onToggleSource,
  uploadError,
  stats,
  metrics,
}: SourcePanelProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isImportingUrl, setIsImportingUrl] = useState(false)
  const [isSavingFaq, setIsSavingFaq] = useState(false)
  const [url, setUrl] = useState('')
  const [faqQuestion, setFaqQuestion] = useState('')
  const [faqAnswer, setFaqAnswer] = useState('')
  const [faqKeywords, setFaqKeywords] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function handleFileChange(file: File | undefined) {
    if (!file || !onUploadFile) {
      return
    }

    setIsUploading(true)
    try {
      await onUploadFile(file)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  async function handleUrlSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const target = url.trim()
    if (!target || !onIngestUrl) {
      return
    }

    setIsImportingUrl(true)
    try {
      await onIngestUrl(target)
      setUrl('')
    } finally {
      setIsImportingUrl(false)
    }
  }

  async function handleFaqSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!onCreateFaq || !faqQuestion.trim() || !faqAnswer.trim()) {
      return
    }

    setIsSavingFaq(true)
    try {
      await onCreateFaq({
        question: faqQuestion.trim(),
        answer: faqAnswer.trim(),
        keywords: faqKeywords
          .split(/[,，]/)
          .map((keyword) => keyword.trim())
          .filter(Boolean),
      })
      setFaqQuestion('')
      setFaqAnswer('')
      setFaqKeywords('')
    } finally {
      setIsSavingFaq(false)
    }
  }

  return (
    <aside className="flex h-full min-h-0 flex-col bg-surface">
      <div className="border-b border-line px-5 py-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold uppercase tracking-[0.12em] text-ink-500">
              知识库
            </h2>
            <p className="mt-1 text-lg font-semibold tracking-tight text-ink-950">
              客服资料与运行状态
            </p>
          </div>
          <span className="rounded-full border border-line bg-mist px-2.5 py-1 text-xs font-medium text-ink-600">
            {sources.length} 条
          </span>
        </div>
      </div>

      {stats ? (
        <div className="grid grid-cols-2 gap-2 border-b border-line px-4 py-4">
          {[
            ['资料', stats.source_count],
            ['分片', stats.chunk_count],
            ['FAQ', stats.faq_count],
            ['工单', stats.ticket_count],
          ].map(([label, value]) => (
            <div
              key={label}
              className="rounded-xl border border-line bg-mist px-3 py-3"
            >
              <p className="text-[11px] font-medium uppercase tracking-wider text-ink-400">
                {label}
              </p>
              <p className="mt-1 text-xl font-semibold tracking-tight text-ink-950">
                {value}
              </p>
            </div>
          ))}
        </div>
      ) : null}

      {metrics ? (
        <div className="border-b border-line px-5 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-400">
            运行指标
          </p>
          <div className="mt-3 space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-ink-500">问答次数</span>
              <span className="font-medium text-ink-900">
                {metrics.total_queries}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-ink-500">平均延迟</span>
              <span className="font-medium text-ink-900">
                {metrics.avg_latency_ms} ms
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-ink-500">有帮助率</span>
              <span className="font-medium text-emerald-600">
                {metrics.feedback_count > 0
                  ? `${Math.round(metrics.helpful_rate * 100)}%`
                  : '暂无'}
              </span>
            </div>
          </div>
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-4">
        <div className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-400">
          资料来源
        </div>
        <div className="space-y-2">
          {sources.map((source) => {
            const status = source.archived
              ? {
                  label: '已停用',
                  className: 'bg-slate-100 text-slate-600 ring-slate-200',
                }
              : statusMeta[source.status]
            const isSelected = source.id === selectedId

            return (
              <button
                key={source.id}
                type="button"
                onClick={() =>
                  setSelectedId((current) =>
                    current === source.id ? null : source.id,
                  )
                }
                className={`w-full rounded-xl border px-3.5 py-3 text-left transition ${
                  isSelected
                    ? 'border-brand-200 bg-brand-50/70 shadow-sm'
                    : 'border-transparent bg-mist hover:border-line hover:bg-white hover:shadow-sm'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-ink-900">
                      {source.title}
                    </p>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span className="text-xs text-ink-500">
                        {source.category}
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[11px] ring-1 ${status.className}`}
                      >
                        {status.label}
                      </span>
                    </div>
                  </div>
                  <ChevronDownIcon
                    className={`mt-0.5 h-4 w-4 shrink-0 text-ink-400 transition-transform ${
                      isSelected ? 'rotate-180' : ''
                    }`}
                  />
                </div>

                {isSelected ? (
                  <div className="mt-3 border-t border-line pt-3">
                    <p className="text-sm leading-6 text-ink-600">
                      {source.description}
                    </p>
                    <div className="mt-3 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2 text-xs text-ink-500">
                        <span>更新：{source.updatedAt}</span>
                        {source.status === 'indexed' ? (
                          <CheckIcon className="h-4 w-4 text-emerald-600" />
                        ) : source.status === 'failed' ? (
                          <AlertIcon className="h-4 w-4 text-rose-500" />
                        ) : null}
                      </div>
                      <div className="flex items-center gap-3">
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700"
                        >
                          <LinkIcon className="h-3.5 w-3.5" />
                          查看
                        </a>
                        {onToggleSource ? (
                          <button
                            type="button"
                            onClick={() =>
                              void onToggleSource(source.id, !source.archived)
                            }
                            className="text-xs font-medium text-rose-600 hover:text-rose-700"
                          >
                            {source.archived ? '恢复' : '停用'}
                          </button>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ) : null}
              </button>
            )
          })}
        </div>
      </div>

      <div className="border-t border-line bg-mist/60 px-5 py-4">
        {onCreateFaq ? (
        <details className="mb-3">
          <summary className="cursor-pointer text-xs font-semibold text-brand-700">
            新增 FAQ
          </summary>
          <form onSubmit={handleFaqSubmit} className="mt-3 space-y-2">
            <input
              value={faqQuestion}
              onChange={(event) => setFaqQuestion(event.target.value)}
              placeholder="标准问题"
              className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
            <textarea
              value={faqAnswer}
              onChange={(event) => setFaqAnswer(event.target.value)}
              placeholder="标准答案"
              rows={3}
              className="w-full resize-none rounded-lg border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
            <input
              value={faqKeywords}
              onChange={(event) => setFaqKeywords(event.target.value)}
              placeholder="关键词，用逗号分隔"
              className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
            <button
              type="submit"
              disabled={isSavingFaq || !faqQuestion.trim() || !faqAnswer.trim()}
              className="w-full rounded-lg bg-ink-950 px-3 py-2 text-sm font-medium text-white transition hover:bg-ink-900 disabled:bg-slate-300"
            >
              {isSavingFaq ? '保存中…' : '保存 FAQ'}
            </button>
          </form>
        </details>
        ) : null}

        {onIngestUrl ? (
        <form onSubmit={handleUrlSubmit} className="mb-3">
          <label
            htmlFor="source-url"
            className="mb-1 block text-xs font-medium text-ink-500"
          >
            导入网页
          </label>
          <div className="flex gap-2">
            <input
              id="source-url"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              placeholder="粘贴公开网页 URL"
              className="min-w-0 flex-1 rounded-lg border border-line bg-white px-3 py-2 text-sm outline-none focus:border-brand-500"
            />
            <button
              type="submit"
              disabled={isImportingUrl || !url.trim()}
              className="shrink-0 rounded-lg border border-line bg-white px-3 py-2 text-sm font-medium text-ink-700 transition hover:border-brand-200 hover:text-brand-700 disabled:text-ink-400"
            >
              {isImportingUrl ? '导入中…' : '导入'}
            </button>
          </div>
        </form>
        ) : null}

        {onUploadFile ? (
        <>
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.html,.htm,.pdf"
          className="hidden"
          onChange={(event) => void handleFileChange(event.target.files?.[0])}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
          className="w-full rounded-lg bg-brand-600 px-3 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 disabled:bg-slate-300"
        >
          {isUploading ? '正在导入…' : '上传资料'}
        </button>
        </>
        ) : null}

        {uploadError ? (
          <p className="mt-2 text-xs text-rose-600">{uploadError}</p>
        ) : null}
      </div>
    </aside>
  )
}
