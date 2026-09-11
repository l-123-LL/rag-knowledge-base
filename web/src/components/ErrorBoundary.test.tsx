import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { ErrorBoundary } from './ErrorBoundary'

function BrokenComponent(): never {
  throw new Error('render failed')
}

describe('ErrorBoundary', () => {
  it('renders a fallback screen when a child throws', () => {
    const consoleError = vi
      .spyOn(console, 'error')
      .mockImplementation(() => undefined)

    render(
      <ErrorBoundary>
        <BrokenComponent />
      </ErrorBoundary>,
    )

    expect(screen.getByText('页面暂时无法显示')).toBeInTheDocument()

    consoleError.mockRestore()
  })
})
