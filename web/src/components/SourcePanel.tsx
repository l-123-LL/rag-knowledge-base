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
  uploadError?: string | null
  stats?: Stats
  metrics?: Metrics
}

const statusMeta = {
  indexed: { label: '已索引', className: 'bg-emerald-50 text-emerald-700' },
  pending: { label: '待处理', className: 'bg-amber-50 text-amber-700' },
  failed: { label: '失败', className: 'bg-rose-50 text-rose-700' },
} as const

export function SourcePanel({
  sources,
  onUploadFile,
  onIngestUrl,
  onCreateFaq,
  uploadError,
  stats,
  metrics,
}: SourcePanelProps) {
  // 当前选中的来源，用于展开或收起详情。
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isImportingUrl, setIsImportingUrl] = useState(false)
  const [url, setUrl] = useState('')
  const [faqQuestion, setFaqQuestion] = useState('')
  const [faqAnswer, setFaqAnswer] = useState('')
  const [faqKeywords, setFaqKeywords] = useState('')
  const [isSavingFaq, setIsSavingFaq] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const selected = sources.find((source) => source.id === selectedId) ?? null

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
    <aside className="flex h-full min-h-0 flex-col bg-surface lg:border-r lg:border-line">
      <div className="border-b border-line px-5 py-5">
        <div className="mb-2 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-ink-900">客服知识库</h2>
            <p className="mt-1 text-xs text-ink-500">企业知识资料</p>
          </div>
          <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-600">
            {sources.length} 条
          </span>
        </div>
      </div>

      {stats ? (
        <div className="grid grid-cols-2 gap-2 border-b border-line px-4 py-3">
          <div className="rounded-lg bg-mist px-3 py-2">
            <p className="text-xs text-ink-500">资料</p>
            <p className="mt-1 text-sm font-semibold text-ink-900">
              {stats.source_count}
            </p>
          </div>
          <div className="rounded-lg bg-mist px-3 py-2">
            <p className="text-xs text-ink-500">分片</p>
            <p className="mt-1 text-sm font-semibold text-ink-900">
              {stats.chunk_count}
            </p>
          </div>
          <div className="rounded-lg bg-mist px-3 py-2">
            <p className="text-xs text-ink-500">FAQ</p>
            <p className="mt-1 text-sm font-semibold text-ink-900">
              {stats.faq_count}
            </p>
          </div>
          <div className="rounded-lg bg-mist px-3 py-2">
            <p className="text-xs text-ink-500">会话</p>
            <p className="mt-1 text-sm font-semibold text-ink-900">
              {stats.session_count}
            </p>
          </div>
        </div>
      ) : null}

      {metrics ? (
        <div className="border-b border-line px-4 py-3">
          <p className="mb-2 text-xs font-medium text-ink-500">运行指标</p>
          <div className="space-y-1 text-xs text-ink-600">
            <div className="flex justify-between">
              <span>问答次数</span>
              <span>{metrics.total_queries}</span>
            </div>
            <div className="flex justify-between">
              <span>平均延迟</span>
              <span>{metrics.avg_latency_ms} ms</span>
            </div>
            <div className="flex justify-between">
              <span>累计 token</span>
              <span>{metrics.total_tokens}</span>
            </div>
            <div className="flex justify-between">
              <span>累计成本</span>
              <span>{metrics.total_cost.toFixed(4)}</span>
            </div>
          </div>
        </div>
      ) : null}

      <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
        <div className="space-y-2">
          {sources.map((source) => {
            const status = statusMeta[source.status]
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
                className={`w-full rounded-card border px-3.5 py-3 text-left transition ${
                  isSelected
                    ? 'border-brand-500 bg-brand-50'
                    : 'border-line bg-white hover:border-slate-300 hover:bg-slate-50'
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
                        className={`rounded-full px-2 py-0.5 text-xs ${status.className}`}
                      >
                        {status.label}
                      </span>
                    </div>
                  </div>
                  <ChevronDownIcon
                    className={`mt-0.5 h-4 w-4 shrink-0 text-ink-500 transition-transform ${
                      isSelected ? 'rotate-180' : ''
                    }`}
                  />
                </div>

                {isSelected ? (
                  <div className="mt-3 border-t border-brand-100 pt-3">
                    <p className="text-sm leading-6 text-ink-600">
                      {source.description}
                    </p>
                    <div className="mt-3 flex items-center gap-2 text-xs text-ink-500">
                      <span>更新：{source.updatedAt}</span>
                      {source.status === 'indexed' ? (
                        <CheckIcon className="h-4 w-4 text-emerald-600" />
                      ) : source.status === 'failed' ? (
                        <AlertIcon className="h-4 w-4 text-rose-500" />
                      ) : null}
                    </div>
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-brand-600 hover:text-brand-700"
                    >
                      <LinkIcon className="h-4 w-4" />
                      查看来源
                    </a>
                  </div>
                ) : null}
              </button>
            )
          })}
        </div>
      </div>

      <div className="border-t border-line px-5 py-4">
        {onCreateFaq ? (
          <details className="mb-3">
            <summary className="cursor-pointer text-xs font-medium text-brand-600">
              新增 FAQ
            </summary>
            <form onSubmit={handleFaqSubmit} className="mt-3 space-y-2">
              <input
                value={faqQuestion}
                onChange={(event) => setFaqQuestion(event.target.value)}
                placeholder="标准问题"
                className="w-full rounded-lg border border-line px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
              <textarea
                value={faqAnswer}
                onChange={(event) => setFaqAnswer(event.target.value)}
                placeholder="标准答案"
                rows={3}
                className="w-full resize-none rounded-lg border border-line px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
              <input
                value={faqKeywords}
                onChange={(event) => setFaqKeywords(event.target.value)}
                placeholder="关键词，用逗号分隔"
                className="w-full rounded-lg border border-line px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
              <button
                type="submit"
                disabled={isSavingFaq || !faqQuestion.trim() || !faqAnswer.trim()}
                className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:bg-slate-300"
              >
                {isSavingFaq ? '保存中…' : '保存 FAQ'}
              </button>
            </form>
          </details>
        ) : null}
        {onIngestUrl ? (
          <form onSubmit={handleUrlSubmit} className="mb-3">
            <label htmlFor="source-url" className="mb-1 block text-xs font-medium text-ink-500">
              导入网页
            </label>
            <div className="flex gap-2">
              <input
                id="source-url"
                value={url}
                onChange={(event) => setUrl(event.target.value)}
                placeholder="粘贴公开网页 URL"
                className="min-w-0 flex-1 rounded-lg border border-line px-3 py-2 text-sm outline-none focus:border-brand-500"
              />
              <button
                type="submit"
                disabled={isImportingUrl || !url.trim()}
                className="shrink-0 rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:bg-slate-300"
              >
                {isImportingUrl ? '导入中…' : '导入'}
              </button>
            </div>
          </form>
        ) : null}
        {onUploadFile ? (
          <div className="mb-3">
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.html,.htm,.pdf"
              className="hidden"
              onChange={(event) =>
                void handleFileChange(event.target.files?.[0])
              }
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="w-full rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:bg-slate-300"
            >
              {isUploading ? '正在导入…' : '上传资料'}
            </button>
          </div>
        ) : null}
        <div className="flex items-start gap-2 text-xs leading-5 text-ink-500">
          <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
          <span>当前为纯前端预览，数据为本地模拟内容。</span>
        </div>
        {uploadError ? (
          <p className="mt-2 text-xs text-rose-600">{uploadError}</p>
        ) : null}
      </div>
    </aside>
  )
}
