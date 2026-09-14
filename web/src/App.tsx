import { useCallback, useEffect, useState } from 'react'
import {
  askQuestion,
  archiveSource,
  createFaq,
  ingestFile,
  ingestUrl,
  getMetrics,
  getStats,
  listSources,
  resetSession,
  sendFeedback,
  streamAsk,
} from './api/client'
import { ChatPanel } from './components/ChatPanel'
import { SourcePanel } from './components/SourcePanel'
import { DatabaseIcon } from './components/icons'
import { mockConversations, mockSources } from './data/mockData'
import type { Conversation, Source } from './types'
import type { Metrics, Stats } from './types'

function createId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
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
  }, [])

  return (
    <div className="min-h-screen bg-canvas text-ink-900">
      <header className="sticky top-0 z-20 border-b border-line bg-surface/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1600px] items-center justify-between px-5 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-ink-950 text-white shadow-sm">
              <DatabaseIcon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-[15px] font-semibold tracking-tight text-ink-950">
                企业智能客服
              </p>
              <p className="text-xs text-ink-500">
                Enterprise Support Console
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-line bg-mist px-3 py-1.5 text-xs text-ink-600 sm:flex">
              <span className="h-2 w-2 rounded-full bg-success" />
              服务在线
            </div>
            <span className="rounded-full border border-brand-100 bg-brand-50 px-3 py-1.5 text-xs font-medium text-brand-700">
              默认租户
            </span>
          </div>
        </div>
      </header>

      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-[1600px]">
        <aside className="hidden w-[340px] shrink-0 border-r border-line bg-surface lg:block">
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
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="h-80 border-b border-line bg-surface lg:hidden">
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
          </div>

          <main className="min-h-[620px] flex-1 lg:min-h-0">
            <ChatPanel
              conversations={conversations}
              error={error}
              isLoading={isLoading}
              mockQuestions={mockConversations}
              onAsk={handleAsk}
              onNewSession={handleNewSession}
              onFeedback={handleFeedback}
            />
          </main>
        </div>
      </div>
    </div>
  )
}
