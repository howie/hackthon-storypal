/**
 * Demo overlay — subtitle bar + scene progress indicator.
 * Rendered on top of the demo visuals.
 */

import type { DemoScene } from '@/data/demoScript'
import type { NarratorStatus } from '@/hooks/useDemoNarrator'

interface DemoOverlayProps {
  currentScene: DemoScene
  totalScenes: number
  narratorStatus: NarratorStatus
  transcript: string
}

export function DemoOverlay({
  currentScene,
  totalScenes,
  narratorStatus,
  transcript,
}: DemoOverlayProps) {
  return (
    <>
      {/* Top bar — scene indicator */}
      <div className="pointer-events-none absolute left-0 right-0 top-0 z-50 flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-black/60 px-4 py-1.5 text-sm font-medium text-white backdrop-blur-sm">
            Scene {currentScene.id} / {totalScenes}
          </div>
          <div className="rounded-full bg-black/40 px-3 py-1.5 text-sm text-white/80 backdrop-blur-sm">
            {currentScene.title}
          </div>
        </div>
        {narratorStatus === 'speaking' && (
          <div className="flex items-center gap-2 rounded-full bg-red-500/80 px-3 py-1.5 text-sm text-white backdrop-blur-sm">
            <span className="h-2 w-2 animate-pulse rounded-full bg-white" />
            Speaking
          </div>
        )}
        {narratorStatus === 'connecting' && (
          <div className="flex items-center gap-2 rounded-full bg-yellow-500/80 px-3 py-1.5 text-sm text-white backdrop-blur-sm">
            Connecting...
          </div>
        )}
      </div>

      {/* Bottom bar — subtitle */}
      {transcript && (
        <div className="pointer-events-none absolute bottom-0 left-0 right-0 z-50 flex justify-center px-8 pb-8">
          <div className="max-w-3xl rounded-xl bg-black/70 px-6 py-3 text-center text-lg leading-relaxed text-white backdrop-blur-sm">
            {transcript}
          </div>
        </div>
      )}

      {/* Progress bar at very bottom */}
      <div className="pointer-events-none absolute bottom-0 left-0 right-0 z-50 h-1">
        <div
          className="h-full bg-gradient-to-r from-indigo-500 to-pink-500 transition-all duration-1000 ease-linear"
          style={{ width: `${(currentScene.id / totalScenes) * 100}%` }}
        />
      </div>
    </>
  )
}
