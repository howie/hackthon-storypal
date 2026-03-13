/**
 * StoryImageViewer
 * Feature: 019-story-pixel-images (US2)
 *
 * Displays the scene image for the current story turn with fade transitions.
 * Finds the nearest turn with an image_path relative to the current turn index.
 * Preloads the next 2 scene images to avoid loading delay on switch.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '@/lib/api'
import * as storypalApi from '@/services/storypalApi'
import type { StoryTurn } from '@/types/storypal'

const IMAGE_HEIGHT_PX = 240
const PRELOAD_AHEAD = 2

interface StoryImageViewerProps {
  sessionId: string
  turns: StoryTurn[]
  currentTurnIndex: number
}

/**
 * Build a mapping of turn index → image turn for quick lookup.
 * Each turn index maps to the *nearest preceding* turn that has an image.
 */
function buildImageMap(turns: StoryTurn[]): Map<number, StoryTurn> {
  const map = new Map<number, StoryTurn>()
  let lastImageTurn: StoryTurn | null = null
  for (let i = 0; i < turns.length; i++) {
    if (turns[i].image_path) {
      lastImageTurn = turns[i]
    }
    if (lastImageTurn) {
      map.set(i, lastImageTurn)
    }
  }
  return map
}

export function StoryImageViewer({ sessionId, turns, currentTurnIndex }: StoryImageViewerProps) {
  const imageMap = useMemo(() => buildImageMap(turns), [turns])
  const [loadedUrls, setLoadedUrls] = useState<Map<string, string>>(new Map())
  const [currentImageId, setCurrentImageId] = useState<string | null>(null)
  const [isFading, setIsFading] = useState(false)
  const preloadedRef = useRef<Set<string>>(new Set())
  const blobUrlsRef = useRef<Map<string, string>>(new Map())

  // Get the image turn for the current position
  const imageTurn = imageMap.get(currentTurnIndex) ?? null
  const newImageId = imageTurn?.id ?? null

  // Load image blob from API
  const loadImage = useCallback(
    async (turn: StoryTurn) => {
      if (!turn.image_path || preloadedRef.current.has(turn.id)) return
      preloadedRef.current.add(turn.id)
      try {
        const url = storypalApi.getTurnImageUrl(sessionId, turn.id)
        const response = await api.get<Blob>(url, { responseType: 'blob' })
        const blobUrl = URL.createObjectURL(response.data)
        blobUrlsRef.current.set(turn.id, blobUrl)
        setLoadedUrls((prev) => new Map(prev).set(turn.id, blobUrl))
      } catch {
        // Image load failure is non-blocking — scene will show without image
        preloadedRef.current.delete(turn.id)
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps -- preloadedRef guard is sufficient; omit loadedUrls to avoid re-render loop
    [sessionId],
  )

  // Preload current + next N images (T033)
  useEffect(() => {
    const turnsWithImages: StoryTurn[] = []
    const seen = new Set<string>()

    // Collect unique image turns from currentTurnIndex forward
    for (let i = currentTurnIndex; i < turns.length && turnsWithImages.length < 1 + PRELOAD_AHEAD; i++) {
      const t = imageMap.get(i)
      if (t && !seen.has(t.id)) {
        seen.add(t.id)
        turnsWithImages.push(t)
      }
    }

    for (const t of turnsWithImages) {
      void loadImage(t)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- sessionId already in deps; loadImage excluded to avoid re-render churn
  }, [currentTurnIndex, turns.length, imageMap, sessionId])

  // Handle fade transition when image changes
  useEffect(() => {
    if (newImageId === currentImageId) return
    setIsFading(true)
    const timer = setTimeout(() => {
      setCurrentImageId(newImageId)
      setIsFading(false)
    }, 150) // Half of 300ms fade — fade out then in
    return () => clearTimeout(timer)
  }, [newImageId, currentImageId])

  // Cleanup blob URLs on unmount
  useEffect(() => {
    const ref = blobUrlsRef
    return () => {
      for (const blobUrl of ref.current.values()) {
        URL.revokeObjectURL(blobUrl)
      }
    }
  }, [])

  const displayTurn = currentImageId ? turns.find((t) => t.id === currentImageId) : null
  const imageUrl = currentImageId ? loadedUrls.get(currentImageId) : null

  if (!displayTurn) return null

  return (
    <div
      className="relative w-full overflow-hidden bg-black/5"
      style={{ height: `${IMAGE_HEIGHT_PX}px` }}
    >
      {imageUrl ? (
        <img
          src={imageUrl}
          alt={displayTurn.scene_description || '場景圖片'}
          className="h-full w-full object-contain transition-opacity duration-300"
          style={{ opacity: isFading ? 0 : 1, imageRendering: 'pixelated' }}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      )}
      {displayTurn.scene_description && (
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-3 py-2">
          <p className="text-xs text-white/90 line-clamp-2">{displayTurn.scene_description}</p>
        </div>
      )}
    </div>
  )
}
