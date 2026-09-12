import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { Conversation } from '../types'
import { AnswerCard } from './AnswerCard'

describe('AnswerCard', () => {
  it('renders the insufficient-data state', () => {
    const conversation: Conversation = {
      id: 'insufficient',
      question: '今天天气如何',
      answer: '当前示例资料不足，暂时无法给出可靠回答。',
      citations: [],
      status: 'insufficient',
    }

    render(<AnswerCard conversation={conversation} />)

    expect(screen.getByText('资料不足')).toBeInTheDocument()
    expect(
      screen.getByText('当前示例资料不足，暂时无法给出可靠回答。'),
    ).toBeInTheDocument()
  })

  it('renders the loading state', () => {
    const conversation: Conversation = {
      id: 'loading',
      question: '如何申请退货？',
      citations: [],
      status: 'loading',
    }

    render(<AnswerCard conversation={conversation} />)

    expect(screen.getByLabelText('正在生成答案')).toBeInTheDocument()
  })
})
