import { useRef, useState, type FormEvent } from 'react'
import type { Metrics, Source, Stats } from '../types'
import { AlertIcon, ChevronDownIcon, FileIcon, LinkIcon } from './icons'

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

// 状态色统一用「圆点 + 文字」，不再给每个来源都套一个带边框的胶囊
const STATUS_META = {
  indexed: { label: '已索引', dot: 'text-emerald-500', text: 'text-emerald-700' },
  pending: { label: '待处理', dot: 'text-amber-500', text: 'text-amber-700' },
  failed: { label: '失败', dot: 'text-rose-500', text: 'text-rose-700' },
} as const

const ARCHIVED = { label: '已停用', dot: 'text-slate-400', text: 'text-slate-500' }

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <p className="t-section">{children}</p>
}

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
      {/* 头部：标题 + 资料数，保持一行，避免占据过多垂直空间 */}
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3.5">
        <div>
          <SectionTitle>知识库</SectionTitle>
          <h2 className="mt-1 text-body font-semibold text-ink-950">
            客服资料与运行状态
          </h2>
        </div>
        <span className="t-num shrink-0 rounded-control border border-line bg-mist px-2 py-1 text-micro font-medium text-ink-600">
          {sources.length} 条
        </span>
      </div>

      {stats ? (
        <div className="grid grid-cols-4 divide-x divide-line border-b border-line">
          {[
            ['资料', stats.source_count],
            ['分片', stats.chunk_count],
            ['FAQ', stats.faq_count],
            ['工单', stats.ticket_count],
          ].map(([label, value]) => (
            <div key={label} className="px-3 py-3">
              <p className="text-micro text-ink-400">{label}</p>
              <p className="t-num mt-1 text-title font-semibold text-ink-950">
                {value}
              </p>
            </div>
          ))}
        </div>
      ) : null}

      {metrics ? (
        <div className="border-b border-line px-4 py-3.5">
          <SectionTitle>运行指标</SectionTitle>
          <dl className="mt-2.5 space-y-1.5 text-ui">
            <div className="flex items-center justify-between">
              <dt className="text-ink-500">问答次数</dt>
              <dd className="t-num font-medium text-ink-900">
                {metrics.total_queries}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-ink-500">平均延迟</dt>
              <dd className="t-num font-medium text-ink-900">
                {metrics.avg_latency_ms} ms
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-ink-500">有帮助率</dt>
              <dd className="t-num font-medium text-emerald-600">
                {metrics.feedback_count > 0
                  ? `${Math.round(metrics.helpful_rate * 100)}%`
                  : '暂无'}
              </dd>
            </div>
          </dl>
        </div>
      ) : null}

      {/* 来源列表：等宽行高 + 状态点，扫描效率优先 */}
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="px-4 pb-2 pt-3.5">
          <SectionTitle>资料来源</SectionTitle>
        </div>
        <ul className="px-2 pb-3">
          {sources.map((source) => {
            // 停用状态优先显示，方便管理员快速识别禁用资料。
            const status = source.archived ? ARCHIVED : STATUS_META[source.status]
            const isSelected = source.id === selectedId

            return (
              <li key={source.id}>
                <button
                  type="button"
                  aria-expanded={isSelected}
                  onClick={() =>
                    setSelectedId((current) =>
                      current === source.id ? null : source.id,
                    )
                  }
                  className={`w-full rounded-card px-2.5 py-2 text-left transition-colors ${
                    isSelected ? 'bg-brand-50/70' : 'hover:bg-mist'
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    <FileIcon className="mt-0.5 h-4 w-4 shrink-0 text-ink-400" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-ui font-medium text-ink-900">
                        {source.title}
                      </p>
                      <div className="mt-0.5 flex items-center gap-2">
                        <span className={`status-dot ${status.dot}`} />
                        <span className={`text-micro ${status.text}`}>
                          {status.label}
                        </span>
                        <span className="truncate text-micro text-ink-400">
                          {source.category}
                        </span>
                      </div>
                    </div>
                    <ChevronDownIcon
                      className={`mt-1 h-3.5 w-3.5 shrink-0 text-ink-400 transition-transform ${
                        isSelected ? 'rotate-180' : ''
                      }`}
                    />
                  </div>

                  {isSelected ? (
                    <div className="mt-2 border-t border-line pt-2">
                      <p className="text-caption leading-6 text-ink-600">
                        {source.description}
                      </p>
                      <div className="mt-2 flex items-center justify-between gap-3">
                        <span className="text-micro text-ink-400">
                          更新：{source.updatedAt}
                        </span>
                        <div className="flex items-center gap-3">
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-micro font-medium text-brand-600 hover:text-brand-700"
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
                              className="text-micro font-medium text-rose-600 hover:text-rose-700"
                            >
                              {source.archived ? '恢复' : '停用'}
                            </button>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  ) : null}
                </button>
              </li>
            )
          })}
        </ul>
      </div>

      <div className="border-t border-line bg-mist/50 px-4 py-3.5">
        <SectionTitle>管理操作</SectionTitle>

        {uploadError ? (
          <p className="mt-2 flex items-start gap-1.5 rounded-control border border-rose-200/70 bg-rose-50 px-2.5 py-2 text-micro text-rose-700">
            <AlertIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {uploadError}
          </p>
        ) : null}

        <div className="mt-2.5 space-y-2.5">
          {/* 管理操作全部按管理员身份条件渲染，普通用户不会看到。 */}
          {onCreateFaq ? (
            <details className="group">
              <summary className="flex cursor-pointer items-center justify-between text-ui font-medium text-ink-700">
                新增 FAQ
                <ChevronDownIcon className="h-3.5 w-3.5 text-ink-400 transition-transform group-open:rotate-180" />
              </summary>
              <form onSubmit={handleFaqSubmit} className="mt-2 space-y-1.5">
                <input
                  value={faqQuestion}
                  onChange={(event) => setFaqQuestion(event.target.value)}
                  placeholder="标准问题"
                  className="w-full rounded-control border border-line bg-surface px-2.5 py-1.5 text-caption outline-none focus:border-brand-300"
                />
                <textarea
                  value={faqAnswer}
                  onChange={(event) => setFaqAnswer(event.target.value)}
                  placeholder="标准答案"
                  rows={3}
                  className="w-full resize-none rounded-control border border-line bg-surface px-2.5 py-1.5 text-caption outline-none focus:border-brand-300"
                />
                <input
                  value={faqKeywords}
                  onChange={(event) => setFaqKeywords(event.target.value)}
                  placeholder="关键词，用逗号分隔"
                  className="w-full rounded-control border border-line bg-surface px-2.5 py-1.5 text-caption outline-none focus:border-brand-300"
                />
                <button
                  type="submit"
                  disabled={
                    isSavingFaq || !faqQuestion.trim() || !faqAnswer.trim()
                  }
                  className="btn-primary w-full justify-center"
                >
                  {isSavingFaq ? '保存中…' : '保存 FAQ'}
                </button>
              </form>
            </details>
          ) : null}

          {onIngestUrl ? (
            <form onSubmit={handleUrlSubmit}>
              <label
                htmlFor="source-url"
                className="mb-1.5 block text-ui font-medium text-ink-700"
              >
                导入网页
              </label>
              <div className="flex gap-1.5">
                <input
                  id="source-url"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="粘贴公开网页 URL"
                  className="min-w-0 flex-1 rounded-control border border-line bg-surface px-2.5 py-1.5 text-caption outline-none focus:border-brand-300"
                />
                <button
                  type="submit"
                  disabled={isImportingUrl || !url.trim()}
                  className="btn-secondary shrink-0"
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
                onChange={(event) =>
                  void handleFileChange(event.target.files?.[0])
                }
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="btn-primary w-full justify-center"
              >
                <FileIcon className="h-4 w-4" />
                {isUploading ? '正在导入…' : '上传资料'}
              </button>
            </>
          ) : null}
        </div>
      </div>
    </aside>
  )
}
