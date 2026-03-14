/**
 * Tutor Page — US5 適齡萬事通
 * Feature: Tutor — AI Voice Q&A for Kids
 *
 * Voice-to-voice interaction with Gemini Live API.
 * Architecture: Browser → Gemini Live WebSocket (direct, no backend hop)
 * Audio: Mic 16kHz PCM16 → Gemini → 24kHz PCM16 → Speaker
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Download, Globe, Mic, MicOff, Sparkles } from 'lucide-react'
import { getTutorV2vConfig, getTutorLiveWsUrl, getTutorGames } from '@/services/tutorApi'
import type { TutorGame } from '@/services/tutorApi'
import { useGeminiLive } from '@/hooks/useGeminiLive'
import { useAudioPlayback } from '@/hooks/useAudioPlayback'
import { useConversationRecorder } from '@/hooks/useConversationRecorder'
import { useMicrophone } from '@/hooks/useMicrophone'
import { AudioDevicePicker } from '@/components/shared/AudioDevicePicker'
import { TutorPromptEditor } from '@/components/tutor/TutorPromptEditor'
import { ParentGuidanceInput } from '@/components/tutor/ParentGuidanceInput'
import { useSettingsStore } from '@/stores/settingsStore'
import { cn } from '@/lib/utils'
import type { GeminiLiveConfig } from '@/hooks/useGeminiLive'

// =============================================================================
// Types
// =============================================================================

interface TranscriptEntry {
  id: string
  role: 'user' | 'ai'
  text: string
}

// =============================================================================
// Quick question chips (for text-input fallback)
// =============================================================================

const QUICK_QUESTIONS = [
  '為什麼天空是藍色的？',
  '恐龍為什麼不見了？',
  '彩虹是怎麼出現的？',
  '為什麼要睡覺？',
  '魚為什麼不會溺水？',
  '月亮為什麼會變形狀？',
]

// =============================================================================
// Component
// =============================================================================

export function TutorPage() {
  const { t } = useTranslation('interaction')

  // ── Config state ─────────────────────────────────────────────────────────
  const [childAge, setChildAge] = useState(4)
  const [selectedVoice, setSelectedVoice] = useState('Kore')
  const [availableVoices, setAvailableVoices] = useState<string[]>(['Kore'])
  const [contentLanguage, setContentLanguage] = useState('zh-TW')
  const [configError, setConfigError] = useState<string | null>(null)
  const [isLoadingConfig, setIsLoadingConfig] = useState(false)

  // ── Game selector state ─────────────────────────────────────────────────
  const [availableGames, setAvailableGames] = useState<TutorGame[]>([])
  const [selectedGame, setSelectedGame] = useState<string | undefined>(undefined)

  // ── Prompt editor state ────────────────────────────────────────────────
  const [systemPrompt, setSystemPrompt] = useState('')
  const [defaultPrompt, setDefaultPrompt] = useState('')
  const [isPromptEdited, setIsPromptEdited] = useState(false)
  const [isPromptPanelOpen, setIsPromptPanelOpen] = useState(true)
  const isPromptEditedRef = useRef(false)

  // Keep ref in sync so the age-change effect reads the latest value
  useEffect(() => {
    isPromptEditedRef.current = isPromptEdited
  }, [isPromptEdited])

  // ── Audio device settings ───────────────────────────────────────────────
  const audioInputDeviceId = useSettingsStore((s) => s.audioInputDeviceId)
  const audioOutputDeviceId = useSettingsStore((s) => s.audioOutputDeviceId)

  // ── Conversation recorder ────────────────────────────────────────────────
  const recorder = useConversationRecorder()

  // ── Transcript state ──────────────────────────────────────────────────────
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([])
  const [liveUserText, setLiveUserText] = useState('')
  const [liveAiText, setLiveAiText] = useState('')
  const transcriptEndRef = useRef<HTMLDivElement>(null)

  // ── Fetch games + prompt preview when age or game changes ────────────────
  useEffect(() => {
    let cancelled = false
    getTutorGames(childAge)
      .then((games) => {
        if (cancelled) return
        setAvailableGames(games)
        // Reset game selection if current game is no longer available
        if (selectedGame && !games.some((g) => g.id === selectedGame)) {
          setSelectedGame(undefined)
        }
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [childAge]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    let cancelled = false
    getTutorV2vConfig(childAge, undefined, selectedGame, contentLanguage).then((config) => {
      if (cancelled) return
      setDefaultPrompt(config.system_prompt)
      if (!isPromptEditedRef.current) {
        setSystemPrompt(config.system_prompt)
      }
    }).catch(() => {
      // Errors are surfaced when actually connecting
    })
    return () => { cancelled = true }
  }, [childAge, selectedGame, contentLanguage])

  // ── Auto-scroll transcript ────────────────────────────────────────────────
  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript, liveUserText, liveAiText])

  // ── Audio playback (24kHz PCM16 from Gemini) ─────────────────────────────
  const base64ToArrayBuffer = useCallback((base64: string): ArrayBuffer => {
    const binary = atob(base64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
    return bytes.buffer
  }, [])

  const audioPlayback = useAudioPlayback({
    sampleRate: 24000,
    channelCount: 1,
    sinkId: audioOutputDeviceId,
  })

  // ── Gemini Live connection ────────────────────────────────────────────────
  const gemini = useGeminiLive({
    onAudioData: useCallback(
      (base64Audio: string) => {
        const pcm16 = base64ToArrayBuffer(base64Audio)
        audioPlayback.queueAudioChunk(pcm16, 'pcm16')
        recorder.addAiChunk(pcm16)
      },
      [base64ToArrayBuffer, audioPlayback, recorder]
    ),
    onInputTranscript: useCallback((text: string) => {
      setLiveUserText((prev) => prev + text)
    }, []),
    onOutputTranscript: useCallback((text: string) => {
      setLiveAiText((prev) => prev + text)
    }, []),
    onTurnComplete: useCallback(() => {
      setLiveUserText((prev) => {
        if (prev.trim()) {
          setTranscript((t) => [
            ...t,
            { id: crypto.randomUUID(), role: 'user', text: prev.trim() },
          ])
        }
        return ''
      })
      setLiveAiText((prev) => {
        if (prev.trim()) {
          setTranscript((t) => [
            ...t,
            { id: crypto.randomUUID(), role: 'ai', text: prev.trim() },
          ])
        }
        return ''
      })
    }, []),
    onInterrupted: useCallback(() => {
      audioPlayback.stop()
    }, [audioPlayback]),
  })

  // ── Microphone (16kHz PCM16) ──────────────────────────────────────────────
  const microphone = useMicrophone({
    sampleRate: 16000,
    channelCount: 1,
    echoCancellation: true,
    noiseSuppression: true,
    deviceId: audioInputDeviceId || undefined,
    onAudioChunk: useCallback(
      (chunk: Float32Array) => {
        gemini.sendAudio(chunk)
        recorder.addUserChunk(chunk, 16000)
      },
      [gemini, recorder]
    ),
  })

  // ── Connect / disconnect ──────────────────────────────────────────────────
  const handleConnect = useCallback(async () => {
    setConfigError(null)
    setIsLoadingConfig(true)
    try {
      const config = await getTutorV2vConfig(childAge, selectedVoice, selectedGame, contentLanguage)
      if (availableVoices.length <= 1) setAvailableVoices(config.available_voices)

      const liveConfig: GeminiLiveConfig = {
        wsUrl: getTutorLiveWsUrl(),
        model: config.model,
        voice: config.voice,
        systemPrompt: systemPrompt || config.system_prompt,
      }
      gemini.connect(liveConfig)
      recorder.clear()
      recorder.start()
      setIsPromptPanelOpen(false)
    } catch (err) {
      setConfigError(err instanceof Error ? err.message : t('tutor.configError'))
    } finally {
      setIsLoadingConfig(false)
    }
  }, [childAge, selectedVoice, selectedGame, contentLanguage, gemini, availableVoices.length, systemPrompt, recorder, t])

  const handleDisconnect = useCallback(() => {
    microphone.stopRecording()
    audioPlayback.stop()
    gemini.disconnect()
    recorder.stop()
    setIsPromptPanelOpen(true)
    setTranscript([])
    setLiveUserText('')
    setLiveAiText('')
  }, [microphone, audioPlayback, gemini, recorder])

  // ── Toggle mic ────────────────────────────────────────────────────────────
  const handleToggleMic = useCallback(async () => {
    console.log('[TutorPage] handleToggleMic called, isRecording:', microphone.isRecording)
    if (microphone.isRecording) {
      microphone.stopRecording()
    } else {
      try {
        await microphone.startRecording()
      } catch (err) {
        console.error('[TutorPage] mic startRecording failed:', err)
      }
    }
  }, [microphone])

  // ── Prompt editor handlers ───────────────────────────────────────────────
  const handleSystemPromptChange = useCallback((value: string) => {
    setSystemPrompt(value)
    setIsPromptEdited(true)
  }, [])

  const handleResetToDefault = useCallback(() => {
    setSystemPrompt(defaultPrompt)
    setIsPromptEdited(false)
  }, [defaultPrompt])

  // ── Parent guidance ─────────────────────────────────────────────────────
  const handleSendGuidance = useCallback(
    (text: string) => {
      if (gemini.status !== 'connected') return
      gemini.sendText('[家長引導] ' + text)
    },
    [gemini]
  )

  // ── Send text (quick question fallback) ───────────────────────────────────
  const handleSendText = useCallback(
    (text: string) => {
      if (!text.trim() || gemini.status !== 'connected') return
      gemini.sendText(text.trim())
      setTranscript((t) => [
        ...t,
        { id: crypto.randomUUID(), role: 'user', text: text.trim() },
      ])
    },
    [gemini]
  )

  const isConnected = gemini.status === 'connected'

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-2xl flex-col">
      {/* Header */}
      <div className="flex items-center gap-3 border-b pb-3">
        <div className="flex-1">
          <h1 className="flex items-center gap-2 text-lg font-semibold">
            <Sparkles className="h-5 w-5 text-primary" />
            {t('tutor.title')}
          </h1>
          <p className="text-xs text-muted-foreground">{t('tutor.subtitle')}</p>
        </div>

        {/* Age selector */}
        <div className="flex items-center gap-1.5">
          <label htmlFor="tutor-age" className="text-xs text-muted-foreground">
            {t('tutor.age')}
          </label>
          <select
            id="tutor-age"
            value={childAge}
            onChange={(e) => setChildAge(Number(e.target.value))}
            disabled={isConnected}
            className="rounded-md border bg-background px-2 py-1 text-sm focus:border-primary focus:outline-none disabled:opacity-50"
          >
            {Array.from({ length: 8 }, (_, i) => i + 1).map((age) => (
              <option key={age} value={age}>
                {age} 歲
              </option>
            ))}
          </select>
        </div>

        {/* Voice selector */}
        <div className="flex items-center gap-1.5">
          <label htmlFor="tutor-voice" className="text-xs text-muted-foreground">
            {t('tutor.voiceLabel')}
          </label>
          <select
            id="tutor-voice"
            value={selectedVoice}
            onChange={(e) => setSelectedVoice(e.target.value)}
            disabled={isConnected}
            className="rounded-md border bg-background px-2 py-1 text-sm focus:border-primary focus:outline-none disabled:opacity-50"
          >
            {availableVoices.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </div>

        {/* Game selector */}
        <div className="flex items-center gap-1.5">
          <label htmlFor="tutor-game" className="text-xs text-muted-foreground">
            {t('tutor.game')}
          </label>
          <select
            id="tutor-game"
            value={selectedGame ?? ''}
            onChange={(e) => setSelectedGame(e.target.value || undefined)}
            disabled={isConnected}
            className="rounded-md border bg-background px-2 py-1 text-sm focus:border-primary focus:outline-none disabled:opacity-50"
          >
            <option value="">{t('tutor.freeChat')}</option>
            {availableGames.map((g) => (
              <option key={g.id} value={g.id}>
                {g.name}
              </option>
            ))}
          </select>
        </div>

        {/* Content language selector */}
        <div className="flex items-center gap-1.5">
          <Globe className="h-3.5 w-3.5 text-muted-foreground" />
          <select
            id="tutor-language"
            value={contentLanguage}
            onChange={(e) => setContentLanguage(e.target.value)}
            disabled={isConnected}
            className="rounded-md border bg-background px-2 py-1 text-sm focus:border-primary focus:outline-none disabled:opacity-50"
          >
            <option value="zh-TW">{t('tutor.langZhTW')}</option>
            <option value="en">{t('tutor.langEn')}</option>
          </select>
        </div>

        {/* Recording indicator / download */}
        {recorder.isRecording && (
          <div className="flex items-center gap-1.5 text-xs text-red-500">
            <div className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
            <span>
              {Math.floor(recorder.durationMs / 60000)}:
              {String(Math.floor((recorder.durationMs % 60000) / 1000)).padStart(2, '0')}
            </span>
          </div>
        )}
        {!isConnected && recorder.hasData && (
          <button
            onClick={recorder.downloadWav}
            className="flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs transition-colors hover:bg-muted"
            title={t('tutor.downloadRecordingTitle')}
          >
            <Download className="h-3.5 w-3.5" />
            {t('tutor.downloadRecording')}
          </button>
        )}

        {/* Audio device picker */}
        <AudioDevicePicker popoverPosition="below" />
      </div>

      {/* Error */}
      {configError && (
        <div className="mt-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {configError}
        </div>
      )}

      {/* Prompt editor (between header and transcript) */}
      <TutorPromptEditor
        systemPrompt={systemPrompt}
        onSystemPromptChange={handleSystemPromptChange}
        isEdited={isPromptEdited}
        isOpen={isPromptPanelOpen}
        onToggleOpen={() => setIsPromptPanelOpen((o) => !o)}
        onResetToDefault={handleResetToDefault}
        disabled={isConnected}
      />

      {/* Transcript area */}
      <div className="min-h-0 flex-1 overflow-y-auto py-4">
        {transcript.length === 0 && !liveUserText && !liveAiText ? (
          /* Empty state */
          <div className="flex h-full flex-col items-center justify-center gap-4">
            {!isConnected ? (
              <>
                <Sparkles className="h-12 w-12 text-muted-foreground/30" />
                <p className="text-sm text-muted-foreground">{t('tutor.connectToStart')}</p>
              </>
            ) : (
              <>
                <Sparkles className="h-12 w-12 text-primary/40" />
                <p className="text-sm font-medium">{t('tutor.tutorReady')}</p>
                <p className="text-xs text-muted-foreground">{t('tutor.tutorReadyHint')}</p>
                {/* Quick questions */}
                <div className="flex max-w-md flex-wrap justify-center gap-2">
                  {QUICK_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      onClick={() => handleSendText(q)}
                      className="rounded-full border bg-card px-3 py-1.5 text-xs transition-colors hover:border-primary/50 hover:bg-primary/5"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        ) : (
          /* Transcript bubbles */
          <div className="space-y-3">
            {transcript.map((entry) => (
              <div
                key={entry.id}
                className={cn('flex', entry.role === 'user' ? 'justify-end' : 'justify-start')}
              >
                <div
                  className={cn(
                    'max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
                    entry.role === 'user'
                      ? 'rounded-br-md bg-primary text-primary-foreground'
                      : 'rounded-bl-md bg-muted'
                  )}
                >
                  {entry.text}
                </div>
              </div>
            ))}

            {/* Live transcripts (streaming) */}
            {liveUserText && (
              <div className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl rounded-br-md bg-primary/70 px-4 py-2.5 text-sm leading-relaxed text-primary-foreground opacity-80">
                  {liveUserText}
                </div>
              </div>
            )}
            {liveAiText && (
              <div className="flex justify-start">
                <div className="max-w-[80%] rounded-2xl rounded-bl-md bg-muted px-4 py-2.5 text-sm leading-relaxed opacity-80">
                  {liveAiText}
                </div>
              </div>
            )}

            <div ref={transcriptEndRef} />
          </div>
        )}
      </div>

      {/* Bottom controls */}
      <div className="flex shrink-0 flex-col items-center gap-3 border-t pt-4">
        {/* Parent guidance input (only when connected) */}
        {isConnected && <ParentGuidanceInput onSendGuidance={handleSendGuidance} />}

        {/* AI speaking indicator */}
        {gemini.isModelSpeaking && (
          <div className="flex items-center gap-1.5 text-sm text-primary">
            <div className="flex gap-0.5">
              {[0, 150, 300, 100].map((delay, i) => (
                <div
                  key={i}
                  className="w-1 animate-pulse rounded-full bg-primary"
                  style={{
                    height: i % 2 === 0 ? '12px' : '18px',
                    animationDelay: `${delay}ms`,
                  }}
                />
              ))}
            </div>
            <span>{t('tutor.aiSpeaking')}</span>
          </div>
        )}

        {/* Mic volume bar */}
        {isConnected && microphone.isRecording && (
          <div className="w-full max-w-xs">
            <div className="h-1.5 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-green-500 transition-all duration-75"
                style={{ width: `${microphone.volume * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Main controls row */}
        <div className="flex items-center gap-4">
          {/* Connect / Disconnect button */}
          {!isConnected ? (
            <button
              key="connect"
              onClick={handleConnect}
              disabled={gemini.status === 'connecting' || gemini.status === 'setup_sent' || isLoadingConfig}
              className="rounded-full bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
              {isLoadingConfig || gemini.status === 'connecting' || gemini.status === 'setup_sent'
                ? t('tutor.connecting')
                : t('tutor.startConversation')}
            </button>
          ) : (
            <>
              {/* Mic toggle button */}
              <button
                key="mic-toggle"
                onClick={handleToggleMic}
                className={cn(
                  'flex h-16 w-16 items-center justify-center rounded-full text-white shadow-lg transition-all',
                  microphone.isRecording
                    ? 'scale-110 bg-red-500 shadow-red-500/40'
                    : 'bg-primary shadow-primary/30 hover:scale-105'
                )}
                title={microphone.isRecording ? t('tutor.stopSpeaking') : t('tutor.startSpeaking')}
              >
                {microphone.isRecording ? (
                  <MicOff className="h-7 w-7" />
                ) : (
                  <Mic className="h-7 w-7" />
                )}
              </button>

              {/* End session button */}
              <button
                key="disconnect"
                onClick={handleDisconnect}
                className="rounded-full border bg-background px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted"
              >
                {t('tutor.endConversation')}
              </button>
            </>
          )}
        </div>

        {gemini.error && (
          <p className="text-xs text-destructive">{gemini.error}</p>
        )}
        {microphone.error !== null && (
          <div className="w-full rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {t('tutor.micError', { error: microphone.error })}
          </div>
        )}
        {isConnected && !microphone.isRecording && (
          <p className="text-xs text-muted-foreground">{t('tutor.clickMicToSpeak')}</p>
        )}
        {microphone.isRecording && (
          <p className="text-xs text-red-500">{t('tutor.recording')}</p>
        )}
      </div>
    </div>
  )
}
