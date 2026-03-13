/**
 * Microphone hook for audio recording.
 * Feature: 004-interaction-module
 *
 * T023: Provides microphone access, recording, and audio streaming.
 *
 * Uses AudioWorklet for low-latency audio processing when supported,
 * with automatic fallback to ScriptProcessorNode for older browsers.
 */

import { useCallback, useEffect, useRef, useState } from 'react'

import {
  createAudioProcessor,
  type AudioProcessorResult,
} from '@/lib/audioProcessor'

// =============================================================================
// Types
// =============================================================================

export interface UseMicrophoneOptions {
  /** Sample rate for audio (default: 16000) */
  sampleRate?: number
  /** Channel count (default: 1) */
  channelCount?: number
  /** Enable noise suppression (default: true, set false for child mode) */
  noiseSuppression?: boolean
  /** Enable echo cancellation (default: true) */
  echoCancellation?: boolean
  /** Enable auto gain control (default: browser decides, true for child mode) */
  autoGainControl?: boolean
  /** Specific audio input device ID (empty string = system default) */
  deviceId?: string
  /** Optimize audio capture for children's voices (disables noise suppression) */
  childMode?: boolean
  /** Callback for audio chunks during recording */
  onAudioChunk?: (chunk: Float32Array, sampleRate: number) => void
  /** Callback for volume level changes (0-1) */
  onVolumeChange?: (volume: number) => void
}

export interface UseMicrophoneReturn {
  /** Whether microphone permission is granted */
  hasPermission: boolean | null
  /** Whether currently recording */
  isRecording: boolean
  /** Current volume level (0-1) */
  volume: number
  /** Error message if any */
  error: string | null
  /** Request microphone permission */
  requestPermission: () => Promise<boolean>
  /** Start recording */
  startRecording: () => Promise<void>
  /** Stop recording */
  stopRecording: () => void
  /** Get recorded audio as Blob */
  getRecordedBlob: () => Blob | null
}

// =============================================================================
// Helpers
// =============================================================================

/** Build a human-readable error message from a getUserMedia error.
 *  Guarantees a non-empty string so callers can always display something. */
function micErrorMessage(err: unknown): string {
  if (err instanceof DOMException) {
    switch (err.name) {
      case 'OverconstrainedError':
        return `麥克風不支援要求的設定（${(err as DOMException & { constraint?: string }).constraint ?? '未知'}），嘗試降級中…`
      case 'NotAllowedError':
        return '麥克風權限被拒絕，請在瀏覽器設定中允許麥克風存取'
      case 'NotFoundError':
        return '找不到麥克風裝置，請確認麥克風已連接'
      case 'NotReadableError':
        return '麥克風被其他應用程式佔用，請關閉其他錄音程式後重試'
    }
  }
  if (err instanceof Error && err.message) {
    return err.message
  }
  return '無法存取麥克風'
}

interface AudioConstraintOptions {
  deviceId?: string
  sampleRate: number
  channelCount: number
  noiseSuppression: boolean
  echoCancellation: boolean
  autoGainControl?: boolean
  relaxed?: boolean
}

/** Build MediaTrackConstraints. When `relaxed`, `exact` becomes `ideal`. */
function buildAudioConstraints(opts: AudioConstraintOptions): MediaTrackConstraints {
  const exactOrIdeal = opts.relaxed ? 'ideal' : 'exact'
  return {
    ...(opts.deviceId ? { deviceId: { [exactOrIdeal]: opts.deviceId } } : {}),
    sampleRate: { ideal: opts.sampleRate },
    channelCount: { [exactOrIdeal]: opts.channelCount },
    noiseSuppression: { ideal: opts.noiseSuppression },
    echoCancellation: { ideal: opts.echoCancellation },
    ...(opts.autoGainControl !== undefined
      ? { autoGainControl: { ideal: opts.autoGainControl } }
      : {}),
  }
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useMicrophone(options: UseMicrophoneOptions = {}): UseMicrophoneReturn {
  const {
    sampleRate = 16000,
    channelCount = 1,
    noiseSuppression: noiseSuppressionOpt = true,
    echoCancellation = true,
    autoGainControl: autoGainControlOpt,
    deviceId,
    childMode = false,
    onAudioChunk,
    onVolumeChange,
  } = options

  // Child mode: disable noise suppression (tuned for adult frequencies,
  // can filter out children's higher-pitched voices) and enable AGC
  // (children speak at inconsistent volumes)
  const noiseSuppression = childMode ? false : noiseSuppressionOpt
  const autoGainControl = childMode ? true : autoGainControlOpt

  const [hasPermission, setHasPermission] = useState<boolean | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [volume, setVolume] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const mediaStreamRef = useRef<MediaStream | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const processorRef = useRef<AudioProcessorResult | null>(null)
  const recordedChunksRef = useRef<Float32Array[]>([])
  const animationFrameRef = useRef<number | null>(null)
  const isRecordingRef = useRef(false)

  // Store callbacks in refs to stabilize function identity
  const onAudioChunkRef = useRef(onAudioChunk)
  onAudioChunkRef.current = onAudioChunk
  const onVolumeChangeRef = useRef(onVolumeChange)
  onVolumeChangeRef.current = onVolumeChange

  // Request microphone permission
  const requestPermission = useCallback(async (): Promise<boolean> => {
    const constraintOpts = { deviceId, sampleRate, channelCount, noiseSuppression, echoCancellation, autoGainControl }
    try {
      setError(null)

      let stream: MediaStream
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: buildAudioConstraints(constraintOpts),
        })
      } catch (strictErr) {
        if (strictErr instanceof DOMException && strictErr.name === 'OverconstrainedError') {
          console.warn('[useMicrophone] requestPermission: strict constraints failed, retrying relaxed')
          stream = await navigator.mediaDevices.getUserMedia({
            audio: buildAudioConstraints({ ...constraintOpts, relaxed: true }),
          })
        } else {
          throw strictErr
        }
      }

      // Permission granted, but we don't need to keep the stream
      stream.getTracks().forEach((track) => track.stop())
      setHasPermission(true)
      return true
    } catch (err) {
      setError(micErrorMessage(err))
      setHasPermission(false)
      return false
    }
  }, [sampleRate, channelCount, noiseSuppression, echoCancellation, autoGainControl, deviceId])

  // Update volume meter
  const updateVolume = useCallback(() => {
    if (!analyserRef.current) return

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount)
    analyserRef.current.getByteFrequencyData(dataArray)

    // Calculate RMS volume
    let sum = 0
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i] * dataArray[i]
    }
    const rms = Math.sqrt(sum / dataArray.length) / 255

    setVolume(rms)
    onVolumeChangeRef.current?.(rms)

    if (isRecordingRef.current) {
      animationFrameRef.current = requestAnimationFrame(updateVolume)
    }
  }, [])

  // Start recording
  const startRecording = useCallback(async () => {
    // Guard against duplicate starts (e.g. from effect re-runs)
    if (isRecordingRef.current) {
      console.warn('[useMicrophone] startRecording skipped: already recording')
      return
    }

    console.log('[useMicrophone] startRecording: requesting getUserMedia...')

    const constraintOpts = { deviceId, sampleRate, channelCount, noiseSuppression, echoCancellation, autoGainControl }
    try {
      setError(null)
      recordedChunksRef.current = []

      // Get microphone stream (try strict constraints first, fallback to relaxed)
      let stream: MediaStream
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: buildAudioConstraints(constraintOpts),
        })
      } catch (strictErr) {
        if (strictErr instanceof DOMException && strictErr.name === 'OverconstrainedError') {
          console.warn('[useMicrophone] strict constraints failed, retrying with relaxed constraints')
          stream = await navigator.mediaDevices.getUserMedia({
            audio: buildAudioConstraints({ ...constraintOpts, relaxed: true }),
          })
        } else {
          throw strictErr
        }
      }

      console.log('[useMicrophone] getUserMedia succeeded')
      mediaStreamRef.current = stream
      setHasPermission(true)

      // Create audio context
      const audioContext = new AudioContext({ sampleRate })
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)

      // Branch A: AnalyserNode for volume metering (stays on main thread)
      const analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      analyserRef.current = analyser
      source.connect(analyser)

      // Branch B: Audio processor for recording (uses AudioWorklet when supported)
      const processor = await createAudioProcessor({
        audioContext,
        source,
        onAudioChunk: (chunk, chunkSampleRate) => {
          // Store for later use
          recordedChunksRef.current.push(chunk)
          // Notify listener via ref to avoid stale closure
          onAudioChunkRef.current?.(chunk, chunkSampleRate)
        },
      })
      processorRef.current = processor

      isRecordingRef.current = true
      setIsRecording(true)
      console.log('[useMicrophone] recording started successfully')

      // Start volume monitoring
      animationFrameRef.current = requestAnimationFrame(updateVolume)
    } catch (err) {
      const message = micErrorMessage(err)
      console.error('[useMicrophone] startRecording failed:', message, err)
      setError(message)
      setHasPermission(false)
    }
  }, [
    sampleRate,
    channelCount,
    noiseSuppression,
    echoCancellation,
    autoGainControl,
    deviceId,
    updateVolume,
  ])

  // Stop recording
  const stopRecording = useCallback(() => {
    // Stop animation frame
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
      animationFrameRef.current = null
    }

    // Cleanup processor (handles both AudioWorklet and ScriptProcessor)
    if (processorRef.current) {
      processorRef.current.cleanup()
      processorRef.current = null
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    // Stop media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = null
    }

    analyserRef.current = null
    isRecordingRef.current = false
    setIsRecording(false)
    setVolume(0)
  }, [])

  // Get recorded audio as Blob
  const getRecordedBlob = useCallback((): Blob | null => {
    if (recordedChunksRef.current.length === 0) return null

    // Merge all chunks
    const totalLength = recordedChunksRef.current.reduce((acc, chunk) => acc + chunk.length, 0)
    const mergedArray = new Float32Array(totalLength)

    let offset = 0
    for (const chunk of recordedChunksRef.current) {
      mergedArray.set(chunk, offset)
      offset += chunk.length
    }

    // Convert to 16-bit PCM
    const pcm16 = new Int16Array(mergedArray.length)
    for (let i = 0; i < mergedArray.length; i++) {
      const s = Math.max(-1, Math.min(1, mergedArray[i]))
      pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }

    return new Blob([pcm16.buffer], { type: 'audio/pcm' })
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording()
    }
  }, [stopRecording])

  return {
    hasPermission,
    isRecording,
    volume,
    error,
    requestPermission,
    startRecording,
    stopRecording,
    getRecordedBlob,
  }
}

export default useMicrophone
