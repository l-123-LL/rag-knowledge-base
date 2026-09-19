import { useCallback, useEffect, useState } from 'react'
import {
  askQuestion,
  archiveSource,
  createFaq,
  decideApproval,
  ingestFile,
  ingestUrl,
  getTrace,
  getMetrics,
  getStats,
  listSources,
  listApprovals,
  resetSession,
  sendFeedback,
  streamAsk,
} from './api/client'
import { ChatPanel } from './components/ChatPanel'
import { ApprovalPanel } from './components/ApprovalPanel'
import { SourcePanel } from './components/SourcePanel'
import { TraceTimeline } from './components/TraceTimeline'
import { ChevronDownIcon, DatabaseIcon } from './components/icons'
import { mockConversations, mockSources } from './data/mockData'
import type { Conversation, Source } from './types'
import type { Metrics, Stats } from './types'
import type { TraceRecord, WorkflowMode } from './types'
import type { ApprovalRecord } from './types'

function createId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

/** 从 URL 读取要分享的 trace_id，例如 /?trace=tr_abc。 */
export function readTraceId(search: string): string | null {
  const value = new URLSearchParams(search).get('trace')
  return value && value.trim() ? value.trim() : null
}

export default function App() {
  // 只有前端配置了管理员 Key 时才渲染管理功能。
  const isAdmin = Boolean(import.meta.env.VITE_ADMIN_API_KEY)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sources, setSources] = useState<Source[]>(mockSources)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [stats, setStats] = useState<Stats | undefined>()
  const [metrics, setMetrics] = useState<Metrics | undefined>()
  // 可选工具工作流：默认 rag，保持与升级前一致。
  const [workflowMode, setWorkflowMode] = useState<WorkflowMode>('rag')
  const [trace, setTrace] = useState<TraceRecord | null>(null)
  const [showTrace, setShowTrace] = useState(false)
  const [approvals, setApprovals] = useState<ApprovalRecord[]>([])
  const [approvalError, setApprovalError] = useState<string | null>(null)

  useEffect(() => {
    // 启动时并行拉取来源、统计和指标，避免请求瀑布。
    let active = true

    Promise.all([listSources(), getStats(), getMetrics()])
      .then(([sourceData, statsData, metricsData]) => {
        if (active) {
          if (sourceData.length > 0) {
            setSources(sourceData)
          }
          setStats(statsData)
          setMetrics(metricsData)
        }
      })
      .catch(() => {
        // 后端不可用时继续使用本地 mock 来源。
      })

    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    // 审批队列只对管理员加载；普通用户视图不请求这个接口。
    if (!isAdmin) {
      return
    }

    let active = true
    listApprovals().then((items) => {
      if (active) {
        setApprovals(items)
      }
    })

    return () => {
      active = false
    }
  }, [isAdmin])

  const handleDecideApproval = useCallback(
    async (approvalId: string, approved: boolean, comment?: string) => {
      setApprovalError(null)
      try {
        const updated = await decideApproval(approvalId, approved, comment)
        if (updated) {
          setApprovals((current) =>
            current.map((item) => (item.id === approvalId ? updated : item)),
          )
        }
        const [statsData, metricsData] = await Promise.all([getStats(), getMetrics()])
        setStats(statsData)
        setMetrics(metricsData)
      } catch {
        setApprovalError('审批操作失败，请确认后端正在运行且管理员 Key 正确。')
      }
    },
    [],
  )

  useEffect(() => {
    // 支持用 ?trace=xxx 直接打开某次执行轨迹，方便分享与截图。
    const sharedTraceId = readTraceId(window.location.search)
    if (!sharedTraceId) {
      return
    }

    let active = true
    getTrace(sharedTraceId).then((record) => {
      if (active && record) {
        setTrace(record)
        setShowTrace(true)
        setWorkflowMode('tools')
      }
    })

    return () => {
      active = false
    }
  }, [])

  const handleFileUpload = useCallback(async (file: File) => {
    setUploadError(null)

    try {
      await ingestFile(file)
      const [data, statsData, metricsData] = await Promise.all([
        listSources(),
        getStats(),
        getMetrics(),
      ])
      setSources(data)
      setStats(statsData)
      setMetrics(metricsData)
    } catch {
      setUploadError('上传失败，请确认后端正在运行。')
    }
  }, [])

  const handleUrlIngest = useCallback(async (url: string) => {
    setUploadError(null)

    try {
      await ingestUrl(url)
      const [data, statsData, metricsData] = await Promise.all([
        listSources(),
        getStats(),
        getMetrics(),
      ])
      setSources(data)
      setStats(statsData)
      setMetrics(metricsData)
    } catch {
      setUploadError('网页导入失败，请确认后端正在运行且链接可访问。')
    }
  }, [])

  const handleNewSession = useCallback(async () => {
    setConversations([])
    setError(null)
    await resetSession()
  }, [])

  const handleCreateFaq = useCallback(
    async (payload: {
      question: string
      answer: string
      keywords: string[]
    }) => {
      setUploadError(null)
      try {
        await createFaq(payload)
        const [statsData, metricsData] = await Promise.all([
          getStats(),
          getMetrics(),
        ])
        setStats(statsData)
        setMetrics(metricsData)
      } catch {
        setUploadError('FAQ 保存失败，请确认后端正在运行。')
      }
    },
    [],
  )

  const handleToggleSource = useCallback(
    async (sourceId: string, archived: boolean) => {
      try {
        await archiveSource(sourceId, archived)
        const [sourceData, statsData, metricsData] = await Promise.all([
          listSources(),
          getStats(),
          getMetrics(),
        ])
        setSources(sourceData)
        setStats(statsData)
        setMetrics(metricsData)
      } catch {
        setUploadError('来源状态更新失败，请确认后端正在运行。')
      }
    },
    [],
  )

  const handleFeedback = useCallback(
    async (question: string, rating: 'up' | 'down') => {
      try {
        await sendFeedback({ question, rating })
      } catch {
        setError('反馈提交失败，请稍后重试。')
      }
    },
    [],
  )

  // 前端预览：先展示加载状态，再用本地示例数据模拟一次问答。
  const handleAsk = useCallback(async (rawQuestion: string) => {
    const question = rawQuestion.trim()

    if (!question) {
      return
    }

    setError(null)

    // 保留一个显式入口，方便演示接口错误状态。
    if (question === '模拟错误') {
      setError('接口暂时不可用，请稍后重试。')
      return
    }

    const pendingConversation: Conversation = {
      id: createId(),
      question,
      citations: [],
      status: 'loading',
    }

    setConversations((current) => [...current, pendingConversation])
    setIsLoading(true)

    // 工具工作流走非流式接口：需要一次拿到 trace_id，再回读完整执行轨迹。
    if (workflowMode === 'tools') {
      try {
        const response = await askQuestion(question, 'tools')
        setConversations((current) =>
          current.map((item) =>
            item.id === pendingConversation.id
              ? {
                  ...item,
                  answer: response.answer,
                  citations: response.citations,
                  status: response.status,
                }
              : item,
          ),
        )
        setTrace(response.trace_id ? await getTrace(response.trace_id) : null)
        setShowTrace(true)
      } catch {
        setError('工具工作流调用失败，请确认后端正在运行。')
      } finally {
        setIsLoading(false)
      }
      return
    }

    // 优先流式回答，失败时回退到普通问答。
    try {
      await streamAsk(question, {
        onSources: (citations) => {
          setConversations((current) =>
            current.map((conversation) =>
              conversation.id === pendingConversation.id
                ? { ...conversation, citations, status: 'done' }
                : conversation,
            ),
          )
        },
        onDelta: (text) => {
          setConversations((current) =>
            current.map((conversation) =>
              conversation.id === pendingConversation.id
                ? {
                    ...conversation,
                    answer: `${conversation.answer ?? ''}${text}`,
                    status: 'done',
                  }
                : conversation,
            ),
          )
        },
      })
    } catch {
      const response = await askQuestion(question)
      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === pendingConversation.id
            ? {
                ...conversation,
                answer: response.answer,
                citations: response.citations,
                status: response.status,
              }
            : conversation,
        ),
      )
    } finally {
      setIsLoading(false)
    }
  }, [workflowMode])

  // 一键转人工：复用问答链路，后端意图路由会直接建工单并返回工单号。
  const handleTransferToHuman = useCallback(() => {
    void handleAsk('我要转人工客服')
  }, [handleAsk])

  return (
    <div className="min-h-screen bg-canvas text-ink-900">
      <header className="sticky top-0 z-20 border-b border-line bg-surface">
        <div className="mx-auto flex h-14 max-w-[1680px] items-center justify-between gap-4 px-4 lg:px-6">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control bg-ink-950 text-white">
              <DatabaseIcon className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-ui font-semibold text-ink-950">
                企业智能客服
              </p>
              <p className="truncate text-micro text-ink-400">
                Enterprise Support Console
              </p>
            </div>
            {isAdmin ? (
              <span className="chip ml-1 border-brand-100 bg-brand-50 text-brand-700">
                管理员
              </span>
            ) : null}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {/* 工作流模式切换：分段控件，选中态用深色实心 */}
            <div
              role="group"
              aria-label="工作流模式"
              className="flex items-center rounded-control border border-line bg-mist p-0.5"
            >
              {(['rag', 'tools'] as const).map((mode) => (
                <button
                  key={mode}
                  type="button"
                  aria-pressed={workflowMode === mode}
                  onClick={() => setWorkflowMode(mode)}
                  className={
                    workflowMode === mode
                      ? 'rounded-[6px] bg-surface px-2.5 py-1 text-caption font-medium text-ink-900 shadow-soft'
                      : 'rounded-[6px] px-2.5 py-1 text-caption font-medium text-ink-500 transition-colors hover:text-ink-800'
                  }
                >
                  {mode === 'rag' ? 'RAG 问答' : '工具工作流'}
                </button>
              ))}
            </div>

            {trace || showTrace ? (
              <button
                type="button"
                aria-pressed={showTrace}
                onClick={() => setShowTrace((current) => !current)}
                className="btn-secondary"
              >
                执行轨迹
              </button>
            ) : null}

            <span className="hidden items-center gap-1.5 rounded-control border border-line px-2 py-1 text-micro text-ink-600 sm:inline-flex">
              <span className="status-dot text-emerald-500" />
              服务在线
            </span>
            <span className="hidden rounded-control border border-line bg-mist px-2 py-1 text-micro text-ink-600 md:inline-block">
              默认租户
            </span>
          </div>
        </div>
      </header>

      <div className="mx-auto flex min-h-[calc(100vh-3.5rem)] max-w-[1680px]">
        <aside className="hidden w-[320px] shrink-0 border-r border-line bg-surface lg:block">
          <SourcePanel
            sources={sources}
            onUploadFile={isAdmin ? handleFileUpload : undefined}
            onIngestUrl={isAdmin ? handleUrlIngest : undefined}
            onCreateFaq={isAdmin ? handleCreateFaq : undefined}
            onToggleSource={isAdmin ? handleToggleSource : undefined}
            uploadError={uploadError}
            stats={stats}
            metrics={metrics}
          />
          {isAdmin ? (
            <ApprovalPanel
              approvals={approvals}
              error={approvalError}
              onDecide={handleDecideApproval}
            />
          ) : null}
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          {/* 窄屏：知识库收进可展开区域，默认把版面留给问答 */}
          <details className="group border-b border-line bg-surface lg:hidden">
            <summary className="flex cursor-pointer items-center justify-between px-4 py-3 text-ui font-medium text-ink-700">
              知识库与运行状态
              <ChevronDownIcon className="h-4 w-4 text-ink-400 transition-transform group-open:rotate-180" />
            </summary>
            <div className="max-h-[65vh] overflow-y-auto">
              <SourcePanel
                sources={sources}
                onUploadFile={isAdmin ? handleFileUpload : undefined}
                onIngestUrl={isAdmin ? handleUrlIngest : undefined}
                onCreateFaq={isAdmin ? handleCreateFaq : undefined}
                onToggleSource={isAdmin ? handleToggleSource : undefined}
                uploadError={uploadError}
                stats={stats}
                metrics={metrics}
              />
              {isAdmin ? (
                <ApprovalPanel
                  approvals={approvals}
                  error={approvalError}
                  onDecide={handleDecideApproval}
                />
              ) : null}
            </div>
          </details>

          <main className="min-h-[620px] flex-1 lg:min-h-0">
            <ChatPanel
              conversations={conversations}
              error={error}
              isLoading={isLoading}
              mockQuestions={mockConversations}
              onAsk={handleAsk}
              onTransfer={handleTransferToHuman}
              onNewSession={handleNewSession}
              onFeedback={handleFeedback}
            />
            {showTrace ? (
              <div className="border-t border-line bg-surface">
                <TraceTimeline trace={trace} onClose={() => setShowTrace(false)} />
              </div>
            ) : null}
          </main>
        </div>
      </div>
    </div>
  )
}
