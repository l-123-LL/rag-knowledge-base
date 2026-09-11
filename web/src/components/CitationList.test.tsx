import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { mockConversations } from '../data/mockData'
import { CitationList } from './CitationList'

describe('CitationList', () => {
  it('shows the first citation by default and toggles it closed', () => {
    const citation = mockConversations[0].citations[0]

    render(<CitationList citations={[citation]} />)

    expect(screen.getByText(citation.snippet)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /流行性感冒诊疗方案/ }))

    expect(screen.queryByText(citation.snippet)).not.toBeInTheDocument()
  })

  it('renders nothing when there are no citations', () => {
    const { container } = render(<CitationList citations={[]} />)

    expect(container).toBeEmptyDOMElement()
  })
})
