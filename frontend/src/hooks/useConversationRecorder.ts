/**
 * Conversation Recorder Hook
 *
 * Records both user and AI audio during a Tutor session.
 * - User audio: 16kHz Float32 → upsampled to 24kHz
 * - AI audio: 24kHz PCM16 (native from Gemini)
 * - Output: single-channel 24kHz WAV file
 */

import { useCallback, useRef, useState } from 'react'

// =============================================================================
// Constants
// =============================================================================

const TARGET_SAMPLE_RATE = 24000

// =============================================================================
// Types
// =============================================================================

export interface UseConversationRecorderReturn {
  /** Whether recording is active */
  isRecording: boolean
  /** Whether there is recorded data available */
  hasData: boolean
  /** Recording duration in milliseconds */
  durationMs: number
  /** Start recording */
  start: () => void
  /** Stop recording */
  stop: () => void
  /** Add a user audio chunk (Float32Array from mic, 16kHz) */
  addUserChunk: (chunk: Float32Array, sampleRate: number) => void
  /** Add an AI audio chunk (PCM16 ArrayBuffer, 24kHz) */
  addAiChunk: (pcm16: ArrayBuffer) => void
  /** Download all recorded audio as WAV */
  downloadWav: () => void
  /** Clear all recorded data */
  clear: () => void
}

// =============================================================================
// Utility: Linear interpolation upsample (16kHz → 24kHz)
// =============================================================================

function upsample(input: Float32Array, fromRate: number, toRate: number): Float32Array {
  if (fromRate === toRate) return input
  const ratio = fromRate / toRate
  const outputLength = Math.round(input.length / ratio)
  const output = new Float32Array(outputLength)
  for (let i = 0; i < outputLength; i++) {
    const srcIndex = i * ratio
    const srcFloor = Math.floor(srcIndex)
    const frac = srcIndex - srcFloor
    const s0 = input[srcFloor] ?? 0
    const s1 = input[Math.min(srcFloor + 1, input.length - 1)] ?? 0
    output[i] = s0 + frac * (s1 - s0)
  }
  return output
}

// =============================================================================
// Utility: PCM16 ArrayBuffer → Float32Array
// =============================================================================

function pcm16ToFloat32(buffer: ArrayBuffer): Float32Array {
  const int16 = new Int16Array(buffer)
  const float32 = new Float32Array(int16.length)
  for (let i = 0; i < int16.length; i++) {
    float32[i] = int16[i] / 32768
  }
  return float32
}

// =============================================================================
// Utility: Float32Array → PCM16 for WAV
// =============================================================================

function float32ToPcm16(float32: Float32Array): Int16Array {
  const int16 = new Int16Array(float32.length)
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]))
    int16[i] = s < 0 ? s * 32768 : s * 32767
  }
  return int16
}

// =============================================================================
// Utility: Build WAV file
// =============================================================================

function buildWav(samples: Float32Array, sampleRate: number): Blob {
  const pcm16 = float32ToPcm16(samples)
  const dataLength = pcm16.length * 2
  const buffer = new ArrayBuffer(44 + dataLength)
  const view = new DataView(buffer)

  // RIFF header
  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataLength, true)
  writeString(view, 8, 'WAVE')

  // fmt subchunk
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true) // subchunk size
  view.setUint16(20, 1, true) // PCM format
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // byte rate
  view.setUint16(32, 2, true) // block align
  view.setUint16(34, 16, true) // bits per sample

  // data subchunk
  writeString(view, 36, 'data')
  view.setUint32(40, dataLength, true)

  // Write PCM data
  const pcmBytes = new Uint8Array(buffer, 44)
  pcmBytes.set(new Uint8Array(pcm16.buffer))

  return new Blob([buffer], { type: 'audio/wav' })
}

function writeString(view: DataView, offset: number, str: string) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i))
  }
}

// =============================================================================
// Hook
// =============================================================================

export function useConversationRecorder(): UseConversationRecorderReturn {
  const [isRecording, setIsRecording] = useState(false)
  const [durationMs, setDurationMs] = useState(0)

  const chunksRef = useRef<Float32Array[]>([])
  const totalSamplesRef = useRef(0)
  const startTimeRef = useRef<number | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const start = useCallback(() => {
    chunksRef.current = []
    totalSamplesRef.current = 0
    startTimeRef.current = Date.now()
    setDurationMs(0)
    setIsRecording(true)

    // Update duration display every 500ms
    timerRef.current = setInterval(() => {
      if (startTimeRef.current) {
        setDurationMs(Date.now() - startTimeRef.current)
      }
    }, 500)
  }, [])

  const stop = useCallback(() => {
    setIsRecording(false)
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    if (startTimeRef.current) {
      setDurationMs(Date.now() - startTimeRef.current)
    }
  }, [])

  const addUserChunk = useCallback((chunk: Float32Array, sampleRate: number) => {
    const resampled =
      sampleRate !== TARGET_SAMPLE_RATE
        ? upsample(chunk, sampleRate, TARGET_SAMPLE_RATE)
        : chunk
    chunksRef.current.push(resampled)
    totalSamplesRef.current += resampled.length
  }, [])

  const addAiChunk = useCallback((pcm16: ArrayBuffer) => {
    const float32 = pcm16ToFloat32(pcm16)
    chunksRef.current.push(float32)
    totalSamplesRef.current += float32.length
  }, [])

  const downloadWav = useCallback(() => {
    const chunks = chunksRef.current
    if (chunks.length === 0) return

    // Merge all chunks into a single Float32Array
    const totalLength = totalSamplesRef.current
    const merged = new Float32Array(totalLength)
    let offset = 0
    for (const chunk of chunks) {
      merged.set(chunk, offset)
      offset += chunk.length
    }

    const blob = buildWav(merged, TARGET_SAMPLE_RATE)

    // Generate filename: tutor-對話-YYYY-MM-DD-HHmm.wav
    const now = new Date()
    const pad = (n: number) => String(n).padStart(2, '0')
    const filename = `tutor-對話-${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}.wav`

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [])

  const clear = useCallback(() => {
    chunksRef.current = []
    totalSamplesRef.current = 0
    startTimeRef.current = null
    setDurationMs(0)
  }, [])

  return {
    isRecording,
    hasData: totalSamplesRef.current > 0,
    durationMs,
    start,
    stop,
    addUserChunk,
    addAiChunk,
    downloadWav,
    clear,
  }
}
