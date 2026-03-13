/**
 * StaticStoryPlayer
 * Feature: StoryPal — 純播放模式播放器
 *
 * Displays all story turns with text highlighting and sequential audio playback.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { ArrowLeft, Download, Loader2, Pause, Play, Volume2, VolumeX } from 'lucide-react'
import axios from 'axios'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import * as storypalApi from '@/services/storypalApi'
import { useSettingsStore } from '@/stores/settingsStore'
import type { StoryTurn } from '@/types/storypal'
import { AudioDevicePicker } from '../shared/AudioDevicePicker'
import { StoryImageViewer } from './StoryImageViewer'

/** Magic-number constants */
const SKIP_TURN_DELAY_MS = 2000
const MAX_CONSECUTIVE_FAILURES = 3
const CHOICE_COUNTDOWN_SECONDS = 5

type AudioWithSinkId = HTMLAudioElement & { setSinkId(id: string): Promise<void> }

async function applySinkId(audio: HTMLAudioElement, deviceId: string) {
  if (!deviceId || !('setSinkId' in audio)) return
  try {
    await (audio as AudioWithSinkId).setSinkId(deviceId)
  } catch (e) {
    console.warn('[StaticStoryPlayer] setSinkId failed, using default device:', e)
    // Auto-reset stale device ID so subsequent turns don't repeat the failure
    if (e instanceof DOMException && e.name === 'NotFoundError') {
      useSettingsStore.getState().setAudioOutputDeviceId('')
    }
  }
}

interface StaticStoryPlayerProps {
  sessionId: string
  turns: StoryTurn[]
  title: string
  onExit: () => void
  onComplete?: () => void
}

export function StaticStoryPlayer({ sessionId, turns, title, onExit, onComplete }: StaticStoryPlayerProps) {
  const [currentTurnIndex, setCurrentTurnIndex] = useState(-1)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isMuted, setIsMuted] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState('')
  const [playbackError, setPlaybackError] = useState('')
  // Branching story: choice prompt pause state
  const [currentChoiceTurn, setCurrentChoiceTurn] = useState<StoryTurn | null>(null)
  const [choiceCountdown, setChoiceCountdown] = useState(0)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const blobUrlRef = useRef<string | null>(null)
  const skipDelayTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const turnRefs = useRef<(HTMLDivElement | null)[]>([])

  const audioOutputDeviceId = useSettingsStore((s) => s.audioOutputDeviceId)

  // Refs to avoid stale closures in audio callbacks
  const isPlayingRef = useRef(false)
  const isPausedMidTrackRef = useRef(false)
  // Monotonically-incrementing counter: each playTurnAt call gets a unique ID.
  // When audio.onended fires it compares its captured ID against the current value;
  // if they differ, a newer call has superseded this one → abort silently.
  // This prevents double-play from rapid user clicks or turns-prop updates. (FE-B#8)
  const playInstanceRef = useRef(0)

  // Keep isPlayingRef in sync with state
  useEffect(() => {
    isPlayingRef.current = isPlaying
  }, [isPlaying])

  // Track failed audio downloads across playback
  const failedTurnCountRef = useRef(0)
  const playedTurnCountRef = useRef(0)

  // Playable turns (exclude child_response, question) — memoized for referential stability
  const playableTurns = useMemo(
    () => turns.filter((t) => t.turn_type !== 'child_response' && t.turn_type !== 'question'),
    [turns]
  )
  const totalTurns = playableTurns.length
  const hasAnyAudio = useMemo(() => playableTurns.some((t) => t.audio_path), [playableTurns])
  const hasAnyImage = useMemo(() => playableTurns.some((t) => t.image_path), [playableTurns])

  // Keep a ref to the latest playableTurns so callbacks captured in onended closures
  // always use current turn data even when the turns prop updates mid-playback. (FE-B#8)
  const playableTurnsRef = useRef(playableTurns)
  const totalTurnsRef = useRef(totalTurns)
  useEffect(() => {
    playableTurnsRef.current = playableTurns
    totalTurnsRef.current = totalTurns
  }, [playableTurns, totalTurns])

  /** Clean up previous audio element, blob URL, pending skip-timer, and choice state */
  const cleanupAudio = useCallback(() => {
    setCurrentChoiceTurn(null)
    setChoiceCountdown(0)
    if (skipDelayTimerRef.current !== null) {
      clearTimeout(skipDelayTimerRef.current)
      skipDelayTimerRef.current = null
    }
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.onended = null
      audioRef.current.onerror = null
      audioRef.current.src = ''
      audioRef.current = null
    }
    if (blobUrlRef.current) {
      URL.revokeObjectURL(blobUrlRef.current)
      blobUrlRef.current = null
    }
  }, [])

  const playTurnAt = useCallback(
    async (index: number) => {
      // Grab a unique instance ID for this invocation.
      // Any subsequent call will increment the counter, making this ID stale.
      const myInstance = ++playInstanceRef.current

      // Clean up previous turn's audio before starting new one
      cleanupAudio()
      isPausedMidTrackRef.current = false

      // Use refs so callbacks always see the latest turns even if props changed.
      const currentPlayableTurns = playableTurnsRef.current
      const currentTotal = totalTurnsRef.current

      if (index >= currentTotal) {
        setIsPlaying(false)
        setCurrentTurnIndex(currentTotal)
        // Check if all turns failed to play audio
        if (failedTurnCountRef.current > 0 && playedTurnCountRef.current === 0) {
          console.warn(
            '[StaticStoryPlayer] All audio loads failed:',
            failedTurnCountRef.current, 'failed,', playedTurnCountRef.current, 'played'
          )
          setPlaybackError('音檔載入失敗，請返回重試')
        }
        failedTurnCountRef.current = 0
        playedTurnCountRef.current = 0
        onComplete?.()
        return
      }

      const turn = currentPlayableTurns[index]
      setCurrentTurnIndex(index)

      // Scroll into view
      turnRefs.current[index]?.scrollIntoView({ behavior: 'smooth', block: 'center' })

      // Branching story: choice_prompt turns without audio show overlay immediately;
      // turns with audio fall through to play first, then show overlay on audio end.
      if (turn.turn_type === 'choice_prompt' && !turn.audio_path) {
        setCurrentChoiceTurn(turn)
        setChoiceCountdown(CHOICE_COUNTDOWN_SECONDS)
        return
      }

      if (!turn.audio_path) {
        // No audio: wait a moment then move to next
        skipDelayTimerRef.current = setTimeout(() => {
          skipDelayTimerRef.current = null
          if (isPlayingRef.current && myInstance === playInstanceRef.current) {
            void playTurnAt(index + 1)
          }
        }, SKIP_TURN_DELAY_MS)
        return
      }

      const audioUrl = storypalApi.getTurnAudioUrl(sessionId, turn.id)
      try {
        const response = await api.get<Blob>(audioUrl, { responseType: 'blob' })

        // Guard: a newer playTurnAt call may have been issued while we were fetching.
        if (myInstance !== playInstanceRef.current || !isPlayingRef.current) return

        const blobUrl = URL.createObjectURL(response.data)
        blobUrlRef.current = blobUrl
        const audio = new Audio(blobUrl)
        audioRef.current = audio
        audio.muted = isMuted
        await applySinkId(audio, audioOutputDeviceId)
        // After audio ends: show choice overlay for choice_prompt turns,
        // otherwise advance to next turn.
        const advanceOrShowChoice = () => {
          if (myInstance !== playInstanceRef.current || !isPlayingRef.current) return
          const currentTurn = playableTurnsRef.current[index]
          if (currentTurn?.turn_type === 'choice_prompt') {
            setCurrentChoiceTurn(currentTurn)
            setChoiceCountdown(CHOICE_COUNTDOWN_SECONDS)
            return
          }
          void playTurnAt(index + 1)
        }
        audio.onended = advanceOrShowChoice
        audio.onerror = advanceOrShowChoice
        playedTurnCountRef.current += 1
        audio.play().catch(advanceOrShowChoice)
      } catch (err) {
        console.error('[StaticStoryPlayer] Audio load/play failed for turn', index, ':', err)
        failedTurnCountRef.current += 1

        // 401 → auth 過期，停止播放讓 interceptor redirect
        if (axios.isAxiosError(err) && err.response?.status === 401) {
          setIsPlaying(false)
          setPlaybackError('登入已過期，請重新登入')
          return
        }

        // 連續失敗 N 次 → 提前停止，避免白跑剩餘 turn
        if (failedTurnCountRef.current >= MAX_CONSECUTIVE_FAILURES) {
          setIsPlaying(false)
          setPlaybackError('音檔載入失敗，請返回重試')
          return
        }

        if (isPlayingRef.current && myInstance === playInstanceRef.current) {
          void playTurnAt(index + 1)
        }
      }
    },
    [sessionId, isMuted, cleanupAudio, audioOutputDeviceId, onComplete]
  )

  const handlePlay = useCallback(() => {
    setPlaybackError('')
    setIsPlaying(true)

    // Resume from pause — just call audio.play()
    if (isPausedMidTrackRef.current && audioRef.current) {
      isPausedMidTrackRef.current = false
      audioRef.current.play().catch(() => {
        // If resume fails, start fresh from this turn
        const startIndex = currentTurnIndex < 0 ? 0 : currentTurnIndex
        void playTurnAt(startIndex)
      })
      return
    }

    // Start fresh from turn
    const startIndex = currentTurnIndex < 0 ? 0 : currentTurnIndex
    void playTurnAt(startIndex)
  }, [currentTurnIndex, playTurnAt])

  const handlePause = useCallback(() => {
    setIsPlaying(false)
    if (audioRef.current && !audioRef.current.paused) {
      audioRef.current.pause()
      isPausedMidTrackRef.current = true
    }
  }, [])

  const handleToggleMute = useCallback(() => {
    setIsMuted((m) => {
      const next = !m
      if (audioRef.current) audioRef.current.muted = next
      return next
    })
  }, [])

  const handleTurnClick = useCallback(
    (index: number) => {
      isPausedMidTrackRef.current = false
      cleanupAudio()
      setCurrentTurnIndex(index)
      if (isPlaying) {
        void playTurnAt(index)
      }
    },
    [isPlaying, playTurnAt, cleanupAudio]
  )

  const handleDownload = useCallback(async () => {
    setIsDownloading(true)
    setDownloadError('')
    try {
      const url = storypalApi.getSessionAudioDownloadUrl(sessionId)
      const response = await api.get<Blob>(url, { responseType: 'blob' })
      const blobUrl = URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = blobUrl
      a.download = `${title || '故事'}.mp3`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(blobUrl)
    } catch (err) {
      console.error('Story audio download failed:', err)
      setDownloadError('音檔下載失敗，請稍後再試')
    } finally {
      setIsDownloading(false)
    }
  }, [sessionId, title])

  /** Shared logic: dismiss choice prompt and advance to next turn */
  const advanceFromChoice = useCallback(() => {
    const idx = currentTurnIndex
    setCurrentChoiceTurn(null)
    setChoiceCountdown(0)
    if (isPlayingRef.current) {
      void playTurnAt(idx + 1)
    }
  }, [currentTurnIndex, playTurnAt])

  // Choice countdown timer
  useEffect(() => {
    if (!currentChoiceTurn || choiceCountdown <= 0) return
    const timer = setTimeout(() => {
      setChoiceCountdown((c) => c - 1)
    }, 1000)
    return () => clearTimeout(timer)
  }, [currentChoiceTurn, choiceCountdown])

  // Auto-continue when countdown reaches 0
  useEffect(() => {
    if (currentChoiceTurn && choiceCountdown === 0) {
      advanceFromChoice()
    }
  }, [choiceCountdown, currentChoiceTurn, advanceFromChoice])

  const handleChoiceSelect = useCallback(
    (_option: string) => {
      advanceFromChoice()
    },
    [advanceFromChoice]
  )

  // Live-switch output device on currently playing audio
  useEffect(() => {
    if (audioRef.current) void applySinkId(audioRef.current, audioOutputDeviceId)
  }, [audioOutputDeviceId])

  // Cleanup on unmount — stop audio, clear timers, and release blob URL
  useEffect(() => {
    return () => {
      isPlayingRef.current = false
      if (skipDelayTimerRef.current !== null) {
        clearTimeout(skipDelayTimerRef.current)
        skipDelayTimerRef.current = null
      }
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.src = ''
        audioRef.current = null
      }
      if (blobUrlRef.current) {
        URL.revokeObjectURL(blobUrlRef.current)
        blobUrlRef.current = null
      }
    }
  }, [])

  const progress = totalTurns > 0 ? ((currentTurnIndex + 1) / totalTurns) * 100 : 0

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 border-b px-4 py-3">
        <button
          onClick={onExit}
          className="flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </button>
        <h2 className="flex-1 truncate text-base font-semibold">{title}</h2>
      </div>

      {/* No-audio banner */}
      {!hasAnyAudio && playableTurns.length > 0 && (
        <div className="mx-4 mt-2 rounded-lg bg-amber-50 px-4 py-2 text-sm text-amber-700 border border-amber-200">
          故事尚未產生音檔，請返回重新合成音訊。
        </div>
      )}

      {/* Playback error banner */}
      {playbackError && (
        <div className="mx-4 mt-2 rounded-lg bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {playbackError}
        </div>
      )}

      {/* Scene image (FR-016: only rendered when at least one turn has an image) */}
      {hasAnyImage && (
        <StoryImageViewer
          sessionId={sessionId}
          turns={playableTurns}
          currentTurnIndex={currentTurnIndex < 0 ? 0 : currentTurnIndex}
        />
      )}

      {/* Story content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {playableTurns.length === 0 ? (
          <div className="py-12 text-center text-sm text-muted-foreground">
            還沒有故事內容
          </div>
        ) : (
          playableTurns.map((turn, index) => (
            <div
              key={turn.id}
              ref={(el) => {
                turnRefs.current[index] = el
              }}
              onClick={() => handleTurnClick(index)}
              className={cn(
                'rounded-lg border p-3 cursor-pointer transition-all',
                index === currentTurnIndex
                  ? 'border-primary bg-primary/5 shadow-sm'
                  : 'border-border hover:border-muted-foreground/30 hover:bg-muted/50'
              )}
            >
              {turn.turn_type === 'choice_prompt' ? (
                <div className="space-y-1.5">
                  <p className="text-xs font-semibold text-amber-600">選擇點</p>
                  <p className="text-sm leading-relaxed">{turn.content}</p>
                  {turn.choice_options && (
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {turn.choice_options.map((opt) => (
                        <span key={opt} className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">
                          {opt}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ) : turn.turn_type === 'narration' ? (
                <p className="text-sm italic text-muted-foreground leading-relaxed">
                  {turn.content}
                </p>
              ) : (
                <div className="space-y-0.5">
                  {turn.character_name && (
                    <p className="text-xs font-semibold text-primary">{turn.character_name}</p>
                  )}
                  <p className="text-sm leading-relaxed">{turn.content}</p>
                </div>
              )}

              {/* Audio indicator */}
              {index === currentTurnIndex && isPlaying && (
                <div className="mt-2 flex items-center gap-1">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-3 w-1 rounded-full bg-primary animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }}
                    />
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* Choice prompt overlay */}
      {currentChoiceTurn && (
        <div className="border-t bg-primary/5 px-4 py-4 space-y-3">
          <p className="text-sm font-medium text-center">{currentChoiceTurn.content}</p>
          <div className="flex justify-center gap-3">
            {(currentChoiceTurn.choice_options ?? []).map((option) => (
              <button
                key={option}
                onClick={() => handleChoiceSelect(option)}
                className="rounded-lg border-2 border-primary bg-white px-4 py-2 text-sm font-medium text-primary shadow-sm transition-all hover:bg-primary hover:text-primary-foreground"
              >
                {option}
              </button>
            ))}
          </div>
          <div className="flex justify-center">
            <span className="text-xs text-muted-foreground">
              {choiceCountdown} 秒後自動繼續...
            </span>
          </div>
        </div>
      )}

      {/* Player controls */}
      <div className="border-t bg-card px-4 py-3 space-y-2">
        {/* Progress bar */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>
            {currentTurnIndex < 0 ? 0 : Math.min(currentTurnIndex + 1, totalTurns)} / {totalTurns}
          </span>
          <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Buttons */}
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={handleToggleMute}
            className="rounded-full p-2 text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            {isMuted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>

          {isPlaying ? (
            <button
              onClick={handlePause}
              className="flex items-center gap-2 rounded-full bg-primary px-6 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90"
            >
              <Pause className="h-4 w-4" />
              暫停
            </button>
          ) : (
            <button
              onClick={handlePlay}
              disabled={totalTurns === 0}
              className="flex items-center gap-2 rounded-full bg-primary px-6 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90 disabled:opacity-50"
            >
              <Play className="h-4 w-4" />
              {currentTurnIndex < 0 ? '開始播放' : currentTurnIndex >= totalTurns ? '重新播放' : '繼續播放'}
            </button>
          )}

          <button
            onClick={() => { void handleDownload() }}
            disabled={isDownloading || totalTurns === 0}
            className="rounded-full p-2 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-50"
            title="下載故事音檔"
          >
            {isDownloading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
          </button>

          <AudioDevicePicker />
        </div>
        {downloadError && (
          <p className="mt-1 text-center text-xs text-destructive">{downloadError}</p>
        )}
      </div>
    </div>
  )
}
