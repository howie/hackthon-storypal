/**
 * StoryPage — 語音故事
 *
 * Manages the full lifecycle: setup (unified form) →
 * generate → review/edit → synthesize → play with StaticStoryPlayer.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft,
  BookOpen,
  ImageIcon,
  Loader2,
  Play,
  RefreshCw,
  Save,
  Sparkles,
} from 'lucide-react'
import {
  QAPlayer,
  StaticStoryPlayer,
  StoryBookViewer,
  StoryPalErrorBoundary,
  StorySetupForm,
} from '@/components/storypal'
import { ConfirmDialog } from '@/components/shared/ConfirmDialog'
import { useConfirmDialog } from '@/hooks/useConfirmDialog'
import { StorySessionList } from '@/components/storypal/StorySessionList'
import type { VoiceMode, StoryMode } from '@/components/storypal/StorySetupForm'
import * as storypalApi from '@/services/storypalApi'
import { useStoryPalStore } from '@/stores/storypalStore'
import type { ChildConfig, QAContent, StorySession, StoryTurn } from '@/types/storypal'
import { cn } from '@/lib/utils'

type PageView = 'list' | 'custom_setup' | 'generating' | 'review' | 'playing' | 'book'

// =============================================================================
// Review view with editable turns
// =============================================================================

function ReviewView({
  session,
  turns,
  error,
  isSynthesizingAudio,
  onBack,
  onSynthesize,
  onTurnsUpdated,
}: {
  session: StorySession | null
  turns: StoryTurn[]
  error: string | null
  isSynthesizingAudio: boolean
  onBack: () => void
  onSynthesize: () => void
  onTurnsUpdated: () => void
}) {
  const { t } = useTranslation('story')
  const editableTurns = useMemo(
    () => turns.filter((t) => t.turn_type !== 'child_response' && t.turn_type !== 'question'),
    [turns]
  )

  const [editedTurns, setEditedTurns] = useState<Record<string, string>>({})
  const [isSavingEdits, setIsSavingEdits] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    const initial: Record<string, string> = {}
    for (const turn of editableTurns) {
      initial[turn.id] = turn.content
    }
    setEditedTurns(initial)
  }, [editableTurns])

  const hasEdits = useMemo(
    () => editableTurns.some((t) => editedTurns[t.id] !== undefined && editedTurns[t.id] !== t.content),
    [editableTurns, editedTurns]
  )

  const handleSaveEdits = useCallback(async () => {
    if (!session) return
    setIsSavingEdits(true)
    setSaveError(null)
    try {
      const changedTurns = editableTurns.filter(
        (t) => editedTurns[t.id] !== undefined && editedTurns[t.id] !== t.content
      )
      await Promise.all(
        changedTurns.map((turn) =>
          storypalApi.updateTurnContent(session.id, turn.id, editedTurns[turn.id])
        )
      )
      onTurnsUpdated()
    } catch {
      setSaveError(t('common:errors.saveFailed'))
    } finally {
      setIsSavingEdits(false)
    }
  }, [session, editableTurns, editedTurns, onTurnsUpdated, t])

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('common:actions.back')}
        </button>
        <h2 className="text-lg font-semibold">{session?.title ?? t('page.storyPreview')}</h2>
      </div>

      {(error || saveError) && (
        <div className="rounded-lg bg-destructive/10 px-4 py-2 text-sm text-destructive">
          {error || saveError}
        </div>
      )}

      <div className="rounded-lg border bg-card divide-y max-h-[60vh] overflow-y-auto">
        {editableTurns.map((turn) => (
          <div key={turn.id} className="px-4 py-3 space-y-0.5">
            {turn.character_name && (
              <p className="text-xs font-semibold text-primary">{turn.character_name}</p>
            )}
            <textarea
              value={editedTurns[turn.id] ?? turn.content}
              onChange={(e) => setEditedTurns((prev) => ({ ...prev, [turn.id]: e.target.value }))}
              className={cn(
                'w-full resize-none rounded border-0 bg-transparent p-0 text-sm leading-relaxed focus:outline-none focus:ring-1 focus:ring-primary/30 focus:rounded-md focus:p-1',
                turn.turn_type === 'narration' && 'italic text-muted-foreground'
              )}
              rows={Math.max(2, Math.ceil((editedTurns[turn.id] ?? turn.content).length / 40))}
            />
          </div>
        ))}
      </div>

      <div className="flex justify-end gap-3">
        <button
          onClick={onBack}
          className="rounded-lg border px-4 py-2 text-sm font-medium hover:bg-muted"
        >
          {t('page.discard')}
        </button>
        {hasEdits && (
          <button
            onClick={() => { void handleSaveEdits() }}
            disabled={isSavingEdits}
            className="flex items-center gap-2 rounded-lg border border-primary px-4 py-2 text-sm font-medium text-primary hover:bg-primary/5 disabled:opacity-50"
          >
            {isSavingEdits ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Save className="h-4 w-4" />
            )}
            {t('page.saveEdits')}
          </button>
        )}
        <button
          onClick={onSynthesize}
          disabled={isSynthesizingAudio || hasEdits}
          title={hasEdits ? t('page.saveFirstHint') : undefined}
          className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {isSynthesizingAudio ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
          ) : (
            <Play className="h-4 w-4" />
          )}
          {t('page.synthAndPlay')}
        </button>
      </div>
    </div>
  )
}

// =============================================================================
// Main StoryPage
// =============================================================================

function StoryPageInner() {
  const { t } = useTranslation('story')
  const {
    sessions,
    session,
    turns,
    templates,
    selectedTemplate,
    selectTemplate,
    isLoadingSessions,
    isLoading,
    isGeneratingStory,
    isSynthesizingAudio,
    isGeneratingImages,
    language,
    defaults,
    jobStatus,
    synthesisProgress,
    imageGenerationProgress,
    generatedContents,
    fetchTemplates,
    fetchSessions,
    fetchDefaults,
    createSession,
    setChildConfig,
    selectSession,
    error,
    triggerGenerateStory,
    triggerSynthesizeAudio,
    triggerGenerateImages,
    loadGeneratedContents,
    stopPollingStatus,
    startListPolling,
    stopListPolling,
    clearError,
    reset,
    setLanguage,
  } = useStoryPalStore()

  const [view, setView] = useState<PageView>('list')
  const [isStoryComplete, setIsStoryComplete] = useState(false)
  const [qaContent, setQaContent] = useState<QAContent | null>(null)
  const { confirm, dialogProps } = useConfirmDialog()

  useEffect(() => {
    fetchTemplates()
    fetchSessions()
    fetchDefaults()
  }, [fetchTemplates, fetchSessions, fetchDefaults])

  // Load generated contents (including Q&A) when entering playing view
  useEffect(() => {
    if (view !== 'playing' || !session) return
    setIsStoryComplete(false)
    setQaContent(null)
    void loadGeneratedContents(session.id)
  }, [view, session, loadGeneratedContents])

  // When generatedContents change and story is complete, fetch full QA content
  useEffect(() => {
    if (!isStoryComplete || !session) return
    const qaItem = generatedContents.find((c) => c.content_type === 'qa')
    if (!qaItem) return
    void storypalApi.getGeneratedContent(session.id, qaItem.id).then((full) => {
      setQaContent(full.content_data as QAContent)
    })
  }, [isStoryComplete, generatedContents, session])

  useEffect(() => () => { stopPollingStatus() }, [stopPollingStatus])

  // List polling for in-progress jobs
  useEffect(() => {
    if (view !== 'list') return
    const hasInProgress = sessions.some((s) => {
      const state = s.story_state
      return state.generation_status === 'generating' || state.synthesis_status === 'synthesizing'
    })
    if (hasInProgress) {
      startListPolling()
    } else {
      stopListPolling()
    }
    return () => { stopListPolling() }
  }, [sessions, view, startListPolling, stopListPolling])

  // State machine: all 'generating' view transitions in one effect to avoid
  // race conditions between generation-completed and synthesis-completed.
  // Priority: synthesis completed > synthesis in-progress > generation completed.
  useEffect(() => {
    if (view !== 'generating') return

    // 1. Synthesis completed → playing (or review if no audio)
    if (jobStatus?.synthesis_status === 'completed') {
      if ((jobStatus.audio_ready_count ?? 0) > 0) {
        setView('playing')
      } else {
        setView('review') // No audio → back to review so user sees the error
      }
      return
    }

    // 2. Synthesis in progress or failed → stay on generating (show progress/error + retry)
    if (isSynthesizingAudio || jobStatus?.synthesis_status === 'failed') return

    // 3. Generation completed (no synthesis started) → review
    if (jobStatus?.generation_status === 'completed') {
      setView('review')
    }
  }, [jobStatus?.generation_status, jobStatus?.synthesis_status, jobStatus?.audio_ready_count, view, isSynthesizingAudio])

  // Auto-trigger QA generation when story generation completes and user selected 'qa'.
  // Mirrors the image generation auto-trigger pattern below.
  const qaGenTriggeredRef = useRef<string | null>(null)
  const { generateQA } = useStoryPalStore()
  useEffect(() => {
    if (!session || view === 'list' || view === 'custom_setup') return
    const genDone =
      jobStatus?.generation_status === 'completed' ||
      session.story_state.generation_status === 'completed'
    const hasQaExtra = session.story_state.content_extras?.includes('qa')
    if (genDone && hasQaExtra && qaGenTriggeredRef.current !== session.id) {
      qaGenTriggeredRef.current = session.id
      void generateQA(session.id)
    }
  }, [session, view, jobStatus?.generation_status, generateQA])

  // Auto-trigger image generation when story generation completes (T027).
  // Covers both live completion (via jobStatus) and session reopen (via story_state).
  // Uses a ref to prevent duplicate triggers across re-renders.
  const imageGenTriggeredRef = useRef<string | null>(null)
  useEffect(() => {
    if (!session || view === 'list' || view === 'custom_setup') return
    const genDone =
      jobStatus?.generation_status === 'completed' ||
      session.story_state.generation_status === 'completed'
    const imgNotStarted =
      !jobStatus?.image_generation_status && !session.story_state.image_generation_status
    if (genDone && imgNotStarted && imageGenTriggeredRef.current !== session.id) {
      imageGenTriggeredRef.current = session.id
      void triggerGenerateImages(session.id)
    }
  }, [session, view, jobStatus?.generation_status, jobStatus?.image_generation_status, triggerGenerateImages])

  // Filter: only sessions that have generation/synthesis (static story sessions)
  const storySessions = useMemo(
    () => sessions.filter((s) => !s.interaction_session_id),
    [sessions]
  )

  const handleSynthesizeAndPlay = useCallback(async () => {
    if (!session) return
    setView('generating')
    await triggerSynthesizeAudio(session.id)
  }, [session, triggerSynthesizeAudio])

  const handleSetupSubmit = useCallback(
    async (config: ChildConfig, voiceMode: VoiceMode, storyMode: StoryMode, extras: string[], ttsProvider?: string) => {
      setChildConfig(config)
      const result = await createSession({
        template_id: selectedTemplate?.id,
        title: selectedTemplate
          ? `${selectedTemplate.name} — ${config.child_name || '小朋友'}`
          : `${config.favorite_character || 'AI'} 的故事`,
        language,
        characters_config: selectedTemplate?.characters,
        child_config: config,
        voice_mode: voiceMode,
        story_mode: storyMode,
        content_extras: extras.length > 0 ? extras : undefined,
        tts_provider: ttsProvider,
      })
      if (result) {
        await triggerGenerateStory(result.id)
        setView('list')
        fetchSessions()
      }
    },
    [selectedTemplate, language, createSession, setChildConfig, triggerGenerateStory, fetchSessions]
  )

  const handleOpenSession = useCallback(
    async (s: StorySession) => {
      await selectSession(s.id)
      const { turns: loadedTurns } = useStoryPalStore.getState()
      const hasAudio = loadedTurns.some((t) => t.audio_path !== null)
      if (hasAudio) {
        setView('playing')
      } else if (loadedTurns.length > 0) {
        setView('review')
      } else {
        setView('custom_setup')
      }
    },
    [selectSession]
  )

  const handleExitPlayer = useCallback(() => {
    reset()
    setView('list')
    fetchSessions()
  }, [reset, fetchSessions])

  // ── Generating view ─────────────────────────────────────────────────────
  if (view === 'generating') {
    return (
      <div className="mx-auto max-w-xl flex flex-col items-center justify-center py-24 space-y-6">
        {isGeneratingStory && (
          <>
            <div className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-sm text-muted-foreground">{t('page.generatingStory')}</p>
          </>
        )}
        {isSynthesizingAudio && (
          <div className="w-full max-w-sm space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{t('page.synthAudio')}</span>
              <span className="font-mono text-primary">
                {synthesisProgress.completed} / {synthesisProgress.total} {t('session.audioSegments')}
              </span>
            </div>
            {synthesisProgress.total > 0 && (
              <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-primary transition-all duration-500"
                  style={{ width: `${(synthesisProgress.completed / synthesisProgress.total) * 100}%` }}
                />
              </div>
            )}
          </div>
        )}
        {isGeneratingImages && (
          <div className="w-full max-w-sm space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <ImageIcon className="h-4 w-4" />
                {t('page.genImages')}
              </span>
              {imageGenerationProgress.total > 0 && (
                <span className="font-mono text-primary">
                  {imageGenerationProgress.completed} / {imageGenerationProgress.total}
                </span>
              )}
            </div>
            {imageGenerationProgress.total > 0 && (
              <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${(imageGenerationProgress.completed / imageGenerationProgress.total) * 100}%` }}
                />
              </div>
            )}
          </div>
        )}
        {error && (
          <div className="space-y-2 text-center">
            <p className="text-sm text-destructive">{error}</p>
            <button
              onClick={() => {
                clearError()
                if (session) {
                  const isGenFailed = jobStatus?.generation_status === 'failed'
                  setView('generating')
                  if (isGenFailed) triggerGenerateStory(session.id)
                  else triggerSynthesizeAudio(session.id)
                }
              }}
              className="text-sm text-primary hover:underline"
            >
              {t('common:actions.retry')}
            </button>
          </div>
        )}
      </div>
    )
  }

  // ── Review view ─────────────────────────────────────────────────────────
  if (view === 'review') {
    return (
      <ReviewView
        session={session}
        turns={turns}
        error={error}
        isSynthesizingAudio={isSynthesizingAudio}
        onBack={() => { reset(); setView('list'); fetchSessions() }}
        onSynthesize={handleSynthesizeAndPlay}
        onTurnsUpdated={() => { if (session) void selectSession(session.id) }}
      />
    )
  }

  // ── Book view (T039 — storybook browsing mode) ─────────────────────────
  if (view === 'book') {
    return (
      <div className="mx-auto max-w-4xl h-[calc(100vh-8rem)] overflow-hidden rounded-lg border bg-card">
        <StoryBookViewer
          sessionId={session?.id ?? ''}
          turns={turns}
          title={session?.title ?? '故事'}
          onExit={() => setView('playing')}
        />
      </div>
    )
  }

  // ── Playing view ────────────────────────────────────────────────────────
  if (view === 'playing') {
    const hasImages = turns.some((t) => t.image_path)
    const imgStatus = jobStatus?.image_generation_status ?? session?.story_state?.image_generation_status
    const canRegenImages = !imgStatus || imgStatus === 'completed' || imgStatus === 'failed'
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <div className="h-[calc(100vh-12rem)] overflow-hidden rounded-lg border bg-card relative">
          <StaticStoryPlayer
            sessionId={session?.id ?? ''}
            turns={turns}
            title={session?.title ?? '故事'}
            onExit={handleExitPlayer}
            onComplete={() => {
              setIsStoryComplete(true)
              if (session) void loadGeneratedContents(session.id)
            }}
          />
          {/* T040 — 繪本模式 + T045 — 重新生成圖片 buttons */}
          <div className="absolute top-3 right-3 flex items-center gap-1.5">
            {canRegenImages && (
              <button
                onClick={async () => {
                  if (!session) return
                  const ok = await confirm({
                    title: t('page.regenImagesTitle'),
                    message: t('page.regenImagesConfirm'),
                  })
                  if (ok) {
                    imageGenTriggeredRef.current = null // Allow re-trigger
                    void triggerGenerateImages(session.id)
                  }
                }}
                disabled={isGeneratingImages}
                title={t('page.regenImagesTitle')}
                className="flex items-center gap-1.5 rounded-lg border bg-card px-3 py-1.5 text-xs font-medium shadow-sm transition-colors hover:bg-accent border-border"
              >
                <RefreshCw className={cn('h-3.5 w-3.5', isGeneratingImages && 'animate-spin')} />
                {t('page.regenImagesBtn')}
              </button>
            )}
            <button
              onClick={() => setView('book')}
              disabled={!hasImages}
              title={hasImages ? t('page.bookModeTitle') : t('page.bookModeWaitImages')}
              className={cn(
                'flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium shadow-sm transition-colors',
                hasImages
                  ? 'bg-card text-foreground hover:bg-accent border-border'
                  : 'bg-muted text-muted-foreground cursor-not-allowed border-transparent'
              )}
            >
              <BookOpen className="h-3.5 w-3.5" />
              {t('page.bookMode')}
            </button>
          </div>
          <ConfirmDialog {...dialogProps} />
        </div>
        {isStoryComplete && qaContent && (
          <QAPlayer qaContent={qaContent} />
        )}
      </div>
    )
  }

  // ── List view ───────────────────────────────────────────────────────────
  if (view === 'list') {
    return (
      <StorySessionList
        sessions={storySessions}
        isLoading={isLoadingSessions}
        headerTitle={t('session.myStories')}
        newButtonLabel={t('session.newStory')}
        emptyMessage={t('session.emptyMessage')}
        onNewStory={() => { selectTemplate(null); setView('custom_setup') }}
        onOpenSession={(s) => { void handleOpenSession(s) }}
        showJobCards
        onReviewSession={async (sess) => { await selectSession(sess.id); setView('review') }}
      />
    )
  }

  // ── Custom setup view (unified: template + personalisation + voice/story mode) ──
  return (
    <div className="mx-auto max-w-7xl">
      <div className="mb-6">
        <button
          onClick={() => { selectTemplate(null); setView('list') }}
          className="mb-4 flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('common:actions.back')}
        </button>
        <div className="flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">{t('page.newStoryTitle')}</h1>
        </div>
        <p className="text-muted-foreground">
          {t('page.newStorySubtitle')}
        </p>
      </div>
      <StorySetupForm
        defaults={defaults}
        templates={templates}
        selectedTemplate={selectedTemplate}
        onSelectTemplate={selectTemplate}
        onSubmit={handleSetupSubmit}
        isLoading={isLoading}
        contentLanguage={language}
        onContentLanguageChange={setLanguage}
      />
    </div>
  )
}

export function StoryPage() {
  return (
    <StoryPalErrorBoundary>
      <StoryPageInner />
    </StoryPalErrorBoundary>
  )
}
