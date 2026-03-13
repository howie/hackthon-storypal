/**
 * DemoPage — Auto-playing demo video page with Gemini Live narration.
 *
 * Orchestrates scene progression, visual rendering, and real-time
 * voice narration via Gemini Live API. Access at /demo (no auth required).
 *
 * Usage: Navigate to /demo, click "Start Demo", screen-record the page.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { Play, SkipForward, RotateCcw, Volume2 } from 'lucide-react'

import { DEMO_SCENES } from '@/data/demoScript'
import type { DemoScene } from '@/data/demoScript'
import { useDemoNarrator } from '@/hooks/useDemoNarrator'
import { DemoTitleCard } from '@/components/demo/DemoTitleCard'
import { DemoOverlay } from '@/components/demo/DemoOverlay'
import {
  MockLandingPage,
  MockStoryTemplates,
  MockStorySetup,
  MockStoryPlaying,
  MockTutorIntro,
  MockTutorLive,
} from '@/components/demo/DemoSceneVisuals'

type DemoState = 'idle' | 'connecting' | 'playing' | 'paused' | 'finished'

export function DemoPage() {
  const [demoState, setDemoState] = useState<DemoState>('idle')
  const [sceneIndex, setSceneIndex] = useState(0)
  const [sceneElapsedMs, setSceneElapsedMs] = useState(0)

  const narrator = useDemoNarrator()
  const sceneTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const abortRef = useRef(false)

  const currentScene = DEMO_SCENES[sceneIndex]

  // Cleanup timer
  const clearSceneTimer = useCallback(() => {
    if (sceneTimerRef.current) {
      clearInterval(sceneTimerRef.current)
      sceneTimerRef.current = null
    }
  }, [])

  // Play a single scene: narrate, wait, advance
  const playScene = useCallback(
    async (scene: DemoScene) => {
      if (abortRef.current) return

      // Start elapsed timer for visual animations
      setSceneElapsedMs(0)
      sceneTimerRef.current = setInterval(() => {
        setSceneElapsedMs((prev) => prev + 100)
      }, 100)

      try {
        // Narrate the scene text
        await narrator.narrate(scene.narration)
      } catch {
        // If narration fails, wait fallback duration
        if (!abortRef.current) {
          await new Promise((resolve) => setTimeout(resolve, scene.fallbackDurationMs))
        }
      }

      if (abortRef.current) return

      // Post-narration delay
      await new Promise((resolve) => setTimeout(resolve, scene.postNarrationDelayMs))

      if (abortRef.current) return

      // Advance to next scene
      clearSceneTimer()
      setSceneElapsedMs(0)

      if (sceneIndex < DEMO_SCENES.length - 1) {
        setSceneIndex((prev) => prev + 1)
      } else {
        setDemoState('finished')
      }
    },
    [narrator, sceneIndex, clearSceneTimer]
  )

  // Auto-play current scene when sceneIndex changes and demo is playing
  useEffect(() => {
    if (demoState !== 'playing') return
    if (narrator.status !== 'ready' && narrator.status !== 'speaking') return

    playScene(DEMO_SCENES[sceneIndex])
  }, [sceneIndex, demoState, narrator.status]) // eslint-disable-line react-hooks/exhaustive-deps

  // Start demo
  const startDemo = useCallback(() => {
    abortRef.current = false
    setSceneIndex(0)
    setSceneElapsedMs(0)
    setDemoState('connecting')
    narrator.connect()
  }, [narrator])

  // When narrator becomes ready, start playing
  useEffect(() => {
    if (demoState === 'connecting' && narrator.status === 'ready') {
      setDemoState('playing')
    }
  }, [demoState, narrator.status])

  // Skip to next scene
  const skipScene = useCallback(() => {
    narrator.stop()
    clearSceneTimer()
    setSceneElapsedMs(0)
    if (sceneIndex < DEMO_SCENES.length - 1) {
      setSceneIndex((prev) => prev + 1)
    } else {
      setDemoState('finished')
    }
  }, [narrator, sceneIndex, clearSceneTimer])

  // Reset demo
  const resetDemo = useCallback(() => {
    abortRef.current = true
    narrator.disconnect()
    clearSceneTimer()
    setSceneIndex(0)
    setSceneElapsedMs(0)
    setDemoState('idle')
  }, [narrator, clearSceneTimer])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current = true
      narrator.disconnect()
      clearSceneTimer()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="relative flex h-screen w-screen flex-col overflow-hidden bg-black">
      {/* Main visual area */}
      <div className="relative flex-1 overflow-hidden">
        <SceneVisual
          scene={currentScene}
          elapsedMs={sceneElapsedMs}
        />

        {/* Overlay (subtitles + progress) — only during playback */}
        {demoState === 'playing' && (
          <DemoOverlay
            currentScene={currentScene}
            totalScenes={DEMO_SCENES.length}
            narratorStatus={narrator.status}
            transcript={narrator.transcript}
          />
        )}
      </div>

      {/* Control bar */}
      <div className="flex items-center justify-between border-t border-white/10 bg-black/90 px-6 py-3">
        <div className="flex items-center gap-3">
          {demoState === 'idle' && (
            <button
              onClick={startDemo}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              <Play className="h-4 w-4" />
              Start Demo
            </button>
          )}
          {demoState === 'connecting' && (
            <div className="flex items-center gap-2 text-sm text-yellow-400">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-yellow-400 border-t-transparent" />
              Connecting to Gemini Live...
            </div>
          )}
          {demoState === 'playing' && (
            <>
              <button
                onClick={skipScene}
                className="flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-2 text-sm text-white hover:bg-white/20"
              >
                <SkipForward className="h-4 w-4" />
                Skip
              </button>
            </>
          )}
          {demoState === 'finished' && (
            <button
              onClick={resetDemo}
              className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              <RotateCcw className="h-4 w-4" />
              Replay
            </button>
          )}
          {demoState !== 'idle' && demoState !== 'finished' && (
            <button
              onClick={resetDemo}
              className="flex items-center gap-1.5 rounded-lg bg-white/10 px-3 py-2 text-sm text-white hover:bg-white/20"
            >
              <RotateCcw className="h-4 w-4" />
              Reset
            </button>
          )}
        </div>

        <div className="flex items-center gap-4 text-sm text-white/60">
          <span>
            Scene {sceneIndex + 1} / {DEMO_SCENES.length}
          </span>
          {narrator.status === 'speaking' && (
            <Volume2 className="h-4 w-4 text-green-400" />
          )}
          {narrator.error && (
            <span className="text-red-400">{narrator.error}</span>
          )}
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Scene visual renderer — maps scene.visual to the correct component
// =============================================================================

function SceneVisual({ scene, elapsedMs }: { scene: DemoScene; elapsedMs: number }) {
  const { visual } = scene

  switch (visual) {
    case 'title':
      return <DemoTitleCard variant="intro" />

    case 'landing': {
      // Cycle highlight through the 3 feature cards
      const highlightIndex = Math.floor(elapsedMs / 4000) % 3
      return <MockLandingPage highlightIndex={highlightIndex} />
    }

    case 'story-templates': {
      // Highlight first template, then auto-select second
      const selectedIndex = elapsedMs > 5000 ? 0 : -1
      return <MockStoryTemplates selectedIndex={selectedIndex} />
    }

    case 'story-setup': {
      // Show form first, then switch to generating view
      const phase = elapsedMs > 8000 ? 'generating' : 'form'
      return <MockStorySetup phase={phase as 'form' | 'generating'} />
    }

    case 'story-playing': {
      // Show player, then switch to book view
      const showBook = elapsedMs > 12000
      return <MockStoryPlaying showBook={showBook} />
    }

    case 'tutor-intro': {
      // Highlight different config elements sequentially
      const elements = ['age', 'voice', 'game', null] as const
      const idx = Math.floor(elapsedMs / 3000) % elements.length
      return <MockTutorIntro highlightElement={elements[idx]} />
    }

    case 'tutor-live': {
      // Progressively reveal transcript entries
      const visibleCount = Math.min(
        Math.floor(elapsedMs / 3000) + 1,
        5
      )
      return <MockTutorLive visibleCount={visibleCount} />
    }

    case 'closing':
      return <DemoTitleCard variant="closing" />

    default:
      return <div className="flex h-full items-center justify-center text-white">Unknown scene</div>
  }
}
