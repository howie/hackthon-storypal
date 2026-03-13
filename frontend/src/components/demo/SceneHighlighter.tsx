/**
 * Visual highlight effect for demo scenes.
 * Provides a glowing border and animated cursor-like pointer.
 */

import { useEffect, useState } from 'react'

interface SceneHighlighterProps {
  /** CSS selector targets to highlight sequentially */
  targets?: string[]
  /** Whether highlighting is active */
  active: boolean
}

export function SceneHighlighter({ targets = [], active }: SceneHighlighterProps) {
  const [currentTarget, setCurrentTarget] = useState(0)

  useEffect(() => {
    if (!active || targets.length === 0) return

    setCurrentTarget(0)
    const interval = setInterval(() => {
      setCurrentTarget((prev) => (prev + 1) % targets.length)
    }, 3000)

    return () => clearInterval(interval)
  }, [active, targets])

  useEffect(() => {
    if (!active || targets.length === 0) return

    const selector = targets[currentTarget]
    const el = document.querySelector(selector)
    if (!el) return

    el.classList.add('demo-highlight')
    return () => {
      el.classList.remove('demo-highlight')
    }
  }, [active, targets, currentTarget])

  return null
}

/**
 * Animated fake cursor for demo scenes.
 * Moves to specified coordinates with smooth transition.
 */
interface DemoCursorProps {
  x: number
  y: number
  visible: boolean
  clicking?: boolean
}

export function DemoCursor({ x, y, visible, clicking = false }: DemoCursorProps) {
  if (!visible) return null

  return (
    <div
      className="pointer-events-none fixed z-[100] transition-all duration-700 ease-in-out"
      style={{ left: x, top: y }}
    >
      {/* Cursor arrow */}
      <svg
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        className={`drop-shadow-lg ${clicking ? 'scale-90' : 'scale-100'} transition-transform duration-150`}
      >
        <path
          d="M5 3L19 12L12 13L9 20L5 3Z"
          fill="white"
          stroke="black"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
      {/* Click ripple */}
      {clicking && (
        <div className="absolute left-1 top-1 h-6 w-6 animate-ping rounded-full bg-indigo-400/50" />
      )}
    </div>
  )
}
