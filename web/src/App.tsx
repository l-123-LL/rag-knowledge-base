import { useCallback, useState } from 'react'
import { ChatPanel } from './components/ChatPanel'
import { SourcePanel } from './components/SourcePanel'
import { DatabaseIcon } from './components/icons'
import { findMockAnswer, mockConversations, mockSources } from './data/mockData'
import type { Conversation } from './types'

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

  // 前端预览：先展示加载状态，再用本地示例数据模拟一次问答。
  const handleAsk = useCallback((rawQuestion: string) => {
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

    // 延迟 650ms 模拟真实后端响应，后续接真实 API 时替换这里即可。
    window.setTimeout(() => {
      const match = findMockAnswer(question)

      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === pendingConversation.id
            ? {
                ...conversation,
                answer: match
                  ? match.answer
                  : '当前示例资料不足，暂时无法给出可靠回答。',
                citations: match?.citations ?? [],
                status: match ? 'done' : 'insufficient',
              }
            : conversation,
        ),
      )
      setIsLoading(false)
    }, 650)
  }, [])

  return (
    <div className="flex min-h-screen bg-mist text-ink-900">
      <header className="hidden h-screen w-[300px] shrink-0 flex-col border-r border-line bg-surface lg:flex">
        <div className="flex h-[72px] items-center gap-3 border-b border-line px-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white">
            <DatabaseIcon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold">医学知识库</p>
            <p className="text-xs text-ink-500">RAG 前端预览</p>
          </div>
        </div>
        <div className="min-h-0 flex-1">
          <SourcePanel sources={mockSources} />
        </div>
      </header>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-[72px] items-center gap-3 border-b border-line bg-surface px-5 lg:hidden">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-white">
            <DatabaseIcon className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold">医学知识库</p>
            <p className="text-xs text-ink-500">RAG 前端预览</p>
          </div>
        </header>

        <div className="h-72 border-b border-line lg:hidden">
          <SourcePanel sources={mockSources} />
        </div>

        <main className="min-h-[620px] flex-1 lg:min-h-0">
          <ChatPanel
            conversations={conversations}
            error={error}
            isLoading={isLoading}
            mockQuestions={mockConversations}
            onAsk={handleAsk}
          />
        </main>
      </div>
    </div>
  )
}
