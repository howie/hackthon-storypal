/**
 * Demo narrator hook — wraps useGeminiLive + useAudioPlayback
 * to provide a simple narrateScene(text) interface.
 *
 * Connects to Gemini Live API and sends text for TTS narration.
 * Returns a promise that resolves when narration audio finishes playing.
 */

import { useCallback, useRef, useState } from 'react'

import { useGeminiLive } from '@/hooks/useGeminiLive'
import { useAudioPlayback } from '@/hooks/useAudioPlayback'
import { getTutorLiveWsUrl } from '@/services/tutorApi'
import {
  NARRATOR_SYSTEM_PROMPT,
  NARRATOR_VOICE,
  NARRATOR_MODEL,
} from '@/data/demoScript'

export type NarratorStatus = 'idle' | 'connecting' | 'ready' | 'speaking' | 'error'

export interface UseDemoNarratorReturn {
  /** Current narrator status */
  status: NarratorStatus
  /** Connect to Gemini Live for narration */
  connect: () => void
  /** Disconnect from Gemini Live */
  disconnect: () => void
  /** Narrate text — resolves when audio playback completes */
  narrate: (text: string) => Promise<void>
  /** Stop current narration */
  stop: () => void
  /** Current narration transcript (output from Gemini) */
  transcript: string
  /** Error message if any */
  error: string | null
}

/** Decode base64 string to ArrayBuffer */
function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i)
  }
  return bytes.buffer as ArrayBuffer
}

export function useDemoNarrator(): UseDemoNarratorReturn {
  const [status, setStatus] = useState<NarratorStatus>('idle')
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState<string | null>(null)

  // Promise resolve/reject for current narration
  const narrationResolveRef = useRef<(() => void) | null>(null)
  const narrationRejectRef = useRef<((err: Error) => void) | null>(null)

  // Audio playback for Gemini audio output (24kHz PCM16)
  const audioPlayback = useAudioPlayback({
    sampleRate: 24000,
    channelCount: 1,
    onPlaybackEnd: () => {
      // Audio finished playing — resolve narration promise
      if (narrationResolveRef.current) {
        narrationResolveRef.current()
        narrationResolveRef.current = null
        narrationRejectRef.current = null
        setStatus('ready')
      }
    },
  })

  // Track whether we've received any audio for the current narration
  const hasReceivedAudioRef = useRef(false)
  // Track turn completion to know when Gemini is done sending audio
  const turnCompleteRef = useRef(false)

  const gemini = useGeminiLive({
    onAudioData: (base64Audio: string) => {
      hasReceivedAudioRef.current = true
      const buffer = base64ToArrayBuffer(base64Audio)
      audioPlayback.queueAudioChunk(buffer)
    },
    onOutputTranscript: (text: string) => {
      setTranscript((prev) => prev + text)
    },
    onTurnComplete: () => {
      turnCompleteRef.current = true
      // If no audio was received (unlikely but safe), resolve immediately
      if (!hasReceivedAudioRef.current && narrationResolveRef.current) {
        narrationResolveRef.current()
        narrationResolveRef.current = null
        narrationRejectRef.current = null
        setStatus('ready')
      }
      // Otherwise, onPlaybackEnd will resolve the promise
    },
    onStatusChange: (geminiStatus) => {
      if (geminiStatus === 'connected') {
        setStatus('ready')
      } else if (geminiStatus === 'connecting' || geminiStatus === 'setup_sent') {
        setStatus('connecting')
      } else if (geminiStatus === 'error') {
        setStatus('error')
        setError('Failed to connect to Gemini Live')
        if (narrationRejectRef.current) {
          narrationRejectRef.current(new Error('Gemini connection error'))
          narrationResolveRef.current = null
          narrationRejectRef.current = null
        }
      }
    },
  })

  const connect = useCallback(() => {
    setError(null)
    setStatus('connecting')
    gemini.connect({
      wsUrl: getTutorLiveWsUrl(),
      model: NARRATOR_MODEL,
      voice: NARRATOR_VOICE,
      systemPrompt: NARRATOR_SYSTEM_PROMPT,
    })
  }, [gemini])

  const disconnect = useCallback(() => {
    audioPlayback.stop()
    gemini.disconnect()
    setStatus('idle')
    setTranscript('')
    if (narrationResolveRef.current) {
      narrationResolveRef.current()
      narrationResolveRef.current = null
      narrationRejectRef.current = null
    }
  }, [gemini, audioPlayback])

  const narrate = useCallback(
    (text: string): Promise<void> => {
      return new Promise((resolve, reject) => {
        if (status !== 'ready' && status !== 'speaking') {
          reject(new Error(`Narrator not ready (status: ${status})`))
          return
        }

        // Reset state for new narration
        setTranscript('')
        hasReceivedAudioRef.current = false
        turnCompleteRef.current = false
        narrationResolveRef.current = resolve
        narrationRejectRef.current = reject
        setStatus('speaking')

        // Send narration text to Gemini Live
        gemini.sendText(text)
      })
    },
    [status, gemini]
  )

  const stop = useCallback(() => {
    audioPlayback.stop()
    if (narrationResolveRef.current) {
      narrationResolveRef.current()
      narrationResolveRef.current = null
      narrationRejectRef.current = null
    }
    setStatus('ready')
  }, [audioPlayback])

  return {
    status,
    connect,
    disconnect,
    narrate,
    stop,
    transcript,
    error,
  }
}
