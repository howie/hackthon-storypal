/**
 * StoryBookViewer
 * Feature: 019-story-pixel-images (US3)
 *
 * Full-screen storybook browsing mode. Each page shows a scene image
 * with its Chinese description text. Supports keyboard navigation,
 * touch swipe gestures, and responsive layout.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, ChevronLeft, ChevronRight } from 'lucide-react'
import { api } from '@/lib/api'
import * as storypalApi from '@/services/storypalApi'
import type { StoryTurn } from '@/types/storypal'
import { cn } from '@/lib/utils'

interface StoryBookViewerProps {
  sessionId: string
  turns: StoryTurn[]
  title: string
  onExit: () => void
}

export function StoryBookViewer({ sessionId, turns, title, onExit }: StoryBookViewerProps) {
  const [currentPage, setCurrentPage] = useState(0)
  const [loadedUrls, setLoadedUrls] = useState<Map<string, string>>(new Map())
  const preloadedRef = useRef<Set<string>>(new Set())
  const touchStartXRef = useRef<number | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Filter turns that have images — these are our "pages"
  const pages = useMemo(() => turns.filter((t) => t.image_path), [turns])
  const totalPages = pages.length
  // +1 for the end page
  const totalWithEnd = totalPages + 1
  const isEndPage = currentPage >= totalPages

  // Load image blob from API
  const loadImage = useCallback(
    async (turn: StoryTurn) => {
      if (!turn.image_path || loadedUrls.has(turn.id) || preloadedRef.current.has(turn.id)) return
      preloadedRef.current.add(turn.id)
      const controller = new AbortController()
      abortControllerRef.current = controller
      try {
        const url = storypalApi.getTurnImageUrl(sessionId, turn.id)
        const response = await api.get<Blob>(url, { responseType: 'blob', signal: controller.signal })
        const blobUrl = URL.createObjectURL(response.data)
        setLoadedUrls((prev) => new Map(prev).set(turn.id, blobUrl))
      } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') return
        preloadedRef.current.delete(turn.id)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sessionId]
  )

  // Preload current + next 2 pages
  useEffect(() => {
    for (let i = currentPage; i < Math.min(currentPage + 3, totalPages); i++) {
      void loadImage(pages[i])
    }
  }, [currentPage, pages, totalPages, loadImage])

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ') {
        e.preventDefault()
        setCurrentPage((p) => Math.min(p + 1, totalWithEnd - 1))
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault()
        setCurrentPage((p) => Math.max(p - 1, 0))
      } else if (e.key === 'Escape') {
        onExit()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [totalWithEnd, onExit])

  // Touch swipe handling
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartXRef.current = e.touches[0].clientX
  }, [])

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      if (touchStartXRef.current === null) return
      const diff = touchStartXRef.current - e.changedTouches[0].clientX
      const threshold = 50
      if (diff > threshold) {
        // Swipe left → next page
        setCurrentPage((p) => Math.min(p + 1, totalWithEnd - 1))
      } else if (diff < -threshold) {
        // Swipe right → previous page
        setCurrentPage((p) => Math.max(p - 1, 0))
      }
      touchStartXRef.current = null
    },
    [totalWithEnd]
  )

  // Cleanup blob URLs and abort pending requests on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
      for (const blobUrl of loadedUrls.values()) {
        URL.revokeObjectURL(blobUrl)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const goBack = useCallback(() => setCurrentPage((p) => Math.max(p - 1, 0)), [])
  const goForward = useCallback(
    () => setCurrentPage((p) => Math.min(p + 1, totalWithEnd - 1)),
    [totalWithEnd]
  )

  const progressPercent = totalWithEnd > 1 ? ((currentPage + 1) / totalWithEnd) * 100 : 100

  if (totalPages === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <p className="text-muted-foreground">尚未生成場景圖片</p>
        <button
          onClick={onExit}
          className="flex items-center gap-1 text-sm text-primary hover:underline"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </button>
      </div>
    )
  }

  return (
    <div
      className="flex h-full flex-col bg-background touch-pan-y"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Header */}
      <div className="flex items-center gap-3 border-b px-4 py-2">
        <button
          onClick={onExit}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </button>
        <h2 className="flex-1 truncate text-sm font-semibold">{title}</h2>
        <span className="text-xs text-muted-foreground">
          {currentPage + 1} / {totalWithEnd}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-1 w-full bg-muted">
        <div
          className="h-full bg-primary transition-all duration-300"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {/* Page content */}
      <div className="flex-1 overflow-hidden">
        {isEndPage ? (
          // End page (T038)
          <div className="flex h-full flex-col items-center justify-center gap-6 p-8">
            <div className="text-6xl">📖</div>
            <h3 className="text-2xl font-bold text-foreground">故事結束</h3>
            <p className="text-sm text-muted-foreground text-center max-w-xs">
              感謝閱讀《{title}》
            </p>
            <button
              onClick={onExit}
              className="mt-4 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              返回故事列表
            </button>
          </div>
        ) : (
          // Scene page — responsive layout (T036)
          <div className="flex h-full flex-col md:flex-row">
            {/* Image */}
            <div className="flex-1 flex items-center justify-center bg-black/5 p-4 min-h-0">
              {loadedUrls.has(pages[currentPage].id) ? (
                <img
                  src={loadedUrls.get(pages[currentPage].id)}
                  alt={pages[currentPage].scene_description || '場景圖片'}
                  className="max-h-full max-w-full object-contain rounded-lg shadow-md"
                  style={{ imageRendering: 'pixelated' }}
                />
              ) : (
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              )}
            </div>

            {/* Text */}
            <div className="flex items-center p-6 md:w-2/5 md:border-l">
              <div className="space-y-3 w-full">
                {pages[currentPage].character_name && (
                  <p className="text-xs font-semibold text-primary uppercase tracking-wider">
                    {pages[currentPage].character_name}
                  </p>
                )}
                <p className="text-base leading-relaxed text-foreground">
                  {pages[currentPage].content}
                </p>
                {pages[currentPage].scene_description && (
                  <p className="text-sm italic text-muted-foreground">
                    {pages[currentPage].scene_description}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Navigation controls (T037) */}
      <div className="flex items-center justify-between border-t px-4 py-3">
        <button
          onClick={goBack}
          disabled={currentPage === 0}
          className={cn(
            'flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
            currentPage === 0
              ? 'text-muted-foreground/40 cursor-not-allowed'
              : 'text-foreground hover:bg-muted'
          )}
        >
          <ChevronLeft className="h-4 w-4" />
          上一頁
        </button>

        {/* Page dots for small page counts, otherwise just numbers */}
        <div className="flex items-center gap-1">
          {totalWithEnd <= 10 ? (
            Array.from({ length: totalWithEnd }, (_, i) => (
              <button
                key={i}
                onClick={() => setCurrentPage(i)}
                className={cn(
                  'h-2 rounded-full transition-all',
                  i === currentPage ? 'w-4 bg-primary' : 'w-2 bg-muted-foreground/30 hover:bg-muted-foreground/50'
                )}
              />
            ))
          ) : (
            <span className="text-sm text-muted-foreground">
              {currentPage + 1} / {totalWithEnd}
            </span>
          )}
        </div>

        <button
          onClick={goForward}
          disabled={currentPage >= totalWithEnd - 1}
          className={cn(
            'flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
            currentPage >= totalWithEnd - 1
              ? 'text-muted-foreground/40 cursor-not-allowed'
              : 'text-foreground hover:bg-muted'
          )}
        >
          下一頁
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
