import { useCallback, useEffect, useState } from 'react'
import {
  askQuestion,
  ingestFile,
  ingestUrl,
  getMetrics,
  getStats,
  listSources,
  resetSession,
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
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sources, setSources] = useState<Source[]>(mockSources)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [stats, setStats] = useState<Stats | undefined>()
  const [metrics, setMetrics] = useState<Metrics | undefined>()

  useEffect(() => {
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
    <div className="flex min-h-screen bg-mist text-ink-900">
      <header className="hidden h-screen w-[300px] shrink-0 flex-col border-r border-line bg-surface lg:flex">
        <div className="flex h-[72px] items-center gap-3 border-b border-line px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white">
            <DatabaseIcon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold">企业智能客服</p>
            <p className="text-xs text-ink-500">知识库问答预览</p>
          </div>
        </div>
        <div className="min-h-0 flex-1">
          <SourcePanel
            sources={sources}
            onUploadFile={handleFileUpload}
            onIngestUrl={handleUrlIngest}
            uploadError={uploadError}
            stats={stats}
            metrics={metrics}
          />
        </div>
      </header>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[72px] items-center gap-3 border-b border-line bg-surface px-5 lg:hidden">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white">
            <DatabaseIcon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold">企业智能客服</p>
            <p className="text-xs text-ink-500">知识库问答预览</p>
          </div>
        </header>

        <div className="h-72 border-b border-line lg:hidden">
          <SourcePanel
            sources={sources}
            onUploadFile={handleFileUpload}
            onIngestUrl={handleUrlIngest}
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
          />
        </main>
      </div>
    </div>
  )
}
