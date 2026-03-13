/**
 * StoryPalErrorBoundary
 * Feature: StoryPal — Error Boundary
 *
 * Class-based React ErrorBoundary for the StoryPal feature.
 * Displays a child-friendly error screen in Traditional Chinese when
 * any rendering error occurs within the StoryPal page tree.
 */

import { Component } from 'react'
import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
}

export class StoryPalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(): State {
    return { hasError: true }
  }

  componentDidCatch(error: Error, info: { componentStack: string }): void {
    // Log for developer diagnostics — do not surface to child user
    console.error('[StoryPalErrorBoundary] Uncaught render error:', error, info.componentStack)
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center gap-6 px-6 text-center">
          {/* Decorative illustration */}
          <div className="flex h-24 w-24 items-center justify-center rounded-full bg-primary/10 text-5xl">
            🧚
          </div>

          <div className="space-y-2">
            <h2 className="text-xl font-bold text-foreground">故事精靈去休息了</h2>
            <p className="text-sm text-muted-foreground">
              不用擔心！重新整理一下，精靈馬上回來陪你說故事。
            </p>
          </div>

          <button
            onClick={() => { window.location.reload() }}
            className="rounded-full bg-primary px-8 py-3 text-sm font-semibold text-primary-foreground shadow-md transition-all hover:bg-primary/90 active:scale-95"
          >
            重新整理
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
