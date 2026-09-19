import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AnswerBody } from './AnswerBody'

describe('AnswerBody', () => {
  it('renders plain text without touching the wording', () => {
    render(<AnswerBody text="收到商品后 7 天内可申请无理由退货。" />)

    expect(
      screen.getByText('收到商品后 7 天内可申请无理由退货。'),
    ).toBeInTheDocument()
  })

  it('renders bold segments instead of showing the asterisks', () => {
    render(<AnswerBody text="定制商品**不支持**无理由退货。" />)

    expect(screen.queryByText(/\*\*/)).not.toBeInTheDocument()
    expect(screen.getByText('不支持').tagName).toBe('STRONG')
  })

  it('renders bullet and ordered lists as real lists', () => {
    render(
      <AnswerBody
        text={'分两种情况：\n- 已保价：按约定规则\n- 未保价：按民事法律\n\n1. 第一步\n2. 第二步'}
      />,
    )

    expect(screen.getAllByRole('listitem')).toHaveLength(4)
    expect(screen.getAllByRole('list')).toHaveLength(2)
  })

  it('keeps paragraphs separated when there is a blank line', () => {
    const { container } = render(<AnswerBody text={'第一段。\n\n第二段。'} />)

    expect(container.querySelectorAll('p')).toHaveLength(2)
  })

  it('renders inline code without HTML injection', () => {
    const { container } = render(
      <AnswerBody text={'参数 `top_k=5`，脚本 <script>alert(1)</script>'} />,
    )

    expect(screen.getByText('top_k=5').tagName).toBe('CODE')
    expect(container.querySelector('script')).toBeNull()
  })
})
