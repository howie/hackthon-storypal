/**
 * StoryGamePage — 語音互動遊戲（實驗）
 *
 * WebSocket-based interactive story mode, extracted from the old StoryPalPage.
 * Flow: browse → select template → playing (WebSocket StoryPlayer + content tabs)
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft,
  BookOpen,
  Gamepad2,
  HelpCircle,
  Music,
  Theater,
} from 'lucide-react'
import {
  InteractiveChoicesDisplay,
  QAPlayer,
  SongOutput,
  StoryPalErrorBoundary,
  StoryPlayer,
} from '@/components/storypal'
import { TemplateBrowser } from '@/components/storypal/TemplateBrowser'
import { StorySessionList } from '@/components/storypal/StorySessionList'
import { useStoryPalStore } from '@/stores/storypalStore'
import type {
  InteractiveChoicesContent,
  QAContent,
  SongContent,
  StorySession,
} from '@/types/storypal'
import { cn } from '@/lib/utils'

type PageView = 'list' | 'browse' | 'playing'
type ContentTab = 'story' | 'song' | 'interactive_choices' | 'qa'

function StoryGamePageInner() {
  const { t } = useTranslation('story')

  const {
    sessions,
    session,
    selectedTemplate,
    isLoadingSessions,
    isLoading,
    language,
    generatedContents,
    isGeneratingContent,
    fetchTemplates,
    fetchSessions,
    createSession,
    selectSession,
    error,
    generateSong,
    generateQA,
    generateInteractiveChoices,
    clearError,
    reset,
  } = useStoryPalStore()

  const [view, setView] = useState<PageView>('list')
  const [activeTab, setActiveTab] = useState<ContentTab>('story')

  useEffect(() => {
    fetchTemplates()
    fetchSessions()
  }, [fetchTemplates, fetchSessions])

  // Filter: only sessions that have an interaction_session_id (WebSocket sessions)
  const gameSessions = useMemo(
    () => sessions.filter((s) => s.interaction_session_id != null),
    [sessions]
  )

  const songContent = generatedContents.find((c) => c.content_type === 'song')?.content_data as SongContent | undefined
  const qaContent = generatedContents.find((c) => c.content_type === 'qa')?.content_data as QAContent | undefined
  const choicesContent = generatedContents.find((c) => c.content_type === 'interactive_choices')?.content_data as InteractiveChoicesContent | undefined

  const handleStartInteractive = useCallback(async () => {
    if (!selectedTemplate) return
    const result = await createSession({
      template_id: selectedTemplate.id,
      title: selectedTemplate.name,
      language,
      characters_config: selectedTemplate.characters,
    })
    if (result) {
      setActiveTab('story')
      setView('playing')
    }
  }, [selectedTemplate, language, createSession])

  const handleOpenSession = useCallback(
    async (s: StorySession) => {
      await selectSession(s.id)
      setActiveTab('story')
      setView('playing')
    },
    [selectSession]
  )

  const handleExitPlayer = useCallback(() => {
    reset()
    setView('list')
    fetchSessions()
  }, [reset, fetchSessions])

  const handleGenerateSong = useCallback(() => {
    if (session) {
      clearError()
      generateSong(session.id)
    }
  }, [session, clearError, generateSong])

  const handleGenerateQA = useCallback(() => {
    if (session) {
      clearError()
      generateQA(session.id)
    }
  }, [session, clearError, generateQA])

  const handleStartReview = useCallback(() => {
    if (session) {
      clearError()
      generateQA(session.id)
      setActiveTab('qa')
    }
  }, [session, clearError, generateQA])

  const handleGenerateChoices = useCallback(() => {
    if (session) {
      clearError()
      generateInteractiveChoices(session.id)
    }
  }, [session, clearError, generateInteractiveChoices])

  // ── Playing view ────────────────────────────────────────────────────────
  if (view === 'playing') {
    const contentTabs: { key: ContentTab; label: string; icon: typeof Music; disabled?: boolean }[] = [
      { key: 'story', label: t('game.tabStory'), icon: BookOpen },
      { key: 'song', label: t('game.tabSong'), icon: Music, disabled: true },
      { key: 'interactive_choices', label: t('game.tabChoices'), icon: Theater },
      { key: 'qa', label: t('game.tabQA'), icon: HelpCircle },
    ]

    return (
      <div className="mx-auto max-w-7xl space-y-4">
        {/* Tabs */}
        <div className="flex items-center gap-1 border-b">
          {contentTabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.key}
                onClick={() => !tab.disabled && setActiveTab(tab.key)}
                disabled={tab.disabled}
                className={cn(
                  'flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors',
                  activeTab === tab.key
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground',
                  tab.disabled
                    ? 'cursor-not-allowed opacity-40'
                    : 'hover:text-foreground'
                )}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
          <div className="ml-auto">
            <button
              onClick={handleExitPlayer}
              className="flex items-center gap-1 rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" />
              {t('game.end')}
            </button>
          </div>
        </div>

        {/* Tab content */}
        {activeTab === 'story' && (
          <div className="h-[calc(100vh-12rem)] overflow-hidden rounded-lg border bg-card">
            <StoryPlayer onExit={handleExitPlayer} onStartReview={handleStartReview} />
          </div>
        )}

        {activeTab === 'song' && (
          <SongOutput
            songContent={songContent ?? null}
            isGenerating={isGeneratingContent}
            error={error}
            onGenerate={handleGenerateSong}
          />
        )}

        {activeTab === 'interactive_choices' && (
          <InteractiveChoicesDisplay
            choicesContent={choicesContent ?? null}
            isGenerating={isGeneratingContent}
            error={error}
            onGenerate={handleGenerateChoices}
          />
        )}

        {activeTab === 'qa' && (
          <QAPlayer
            qaContent={qaContent ?? null}
            isGenerating={isGeneratingContent}
            error={error}
            onGenerate={handleGenerateQA}
          />
        )}
      </div>
    )
  }

  // ── List view ───────────────────────────────────────────────────────────
  if (view === 'list') {
    return (
      <StorySessionList
        sessions={gameSessions}
        isLoading={isLoadingSessions}
        headerTitle={t('game.title')}
        newButtonLabel={t('game.startInteraction')}
        emptyMessage={t('game.emptyMessage')}
        onNewStory={() => setView('browse')}
        onOpenSession={(s) => { void handleOpenSession(s) }}
      />
    )
  }

  // ── Browse view ─────────────────────────────────────────────────────────
  return (
    <TemplateBrowser
      onBack={() => setView('list')}
      title={t('game.selectTemplate')}
      subtitle={t('game.selectTemplateSubtitle')}
      actionButtons={
        <button
          onClick={() => { void handleStartInteractive() }}
          disabled={isLoading}
          className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground shadow-lg transition-all hover:bg-primary/90 disabled:opacity-50"
        >
          {isLoading ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
          ) : (
            <Gamepad2 className="h-4 w-4" />
          )}
          {t('game.startInteraction')}
        </button>
      }
    />
  )
}

export function StoryGamePage() {
  return (
    <StoryPalErrorBoundary>
      <StoryGamePageInner />
    </StoryPalErrorBoundary>
  )
}
