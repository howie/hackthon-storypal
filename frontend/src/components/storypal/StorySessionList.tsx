/**
 * StorySessionList
 * Shared component for displaying story sessions with job cards and ready sessions.
 * Used by StoryPage (with job cards) and StoryGamePage (simplified).
 */

import type { ReactNode } from 'react'
import {
  AlertTriangle,
  BookOpen,
  Clock,
  Eye,
  FileText,
  Loader2,
  Music,
  Plus,
  Sparkles,
} from 'lucide-react'
import { useStoryPalStore } from '@/stores/storypalStore'
import type { StorySession } from '@/types/storypal'
import { cn } from '@/lib/utils'

// =============================================================================
// Job state classification
// =============================================================================

type JobState = 'generating' | 'needs_synthesis' | 'synthesizing' | 'gen_failed' | 'synth_failed'

export function getSessionJobState(s: StorySession): JobState | null {
  const state = s.story_state
  if (state.generation_status === 'generating') return 'generating'
  if (state.synthesis_status === 'synthesizing') return 'synthesizing'
  if (state.generation_status === 'failed') return 'gen_failed'
  if (state.synthesis_status === 'failed') return 'synth_failed'
  if (state.generation_status === 'completed' && !state.synthesis_status) return 'needs_synthesis'
  return null
}

function JobCard({ session, onReview }: { session: StorySession; onReview?: (s: StorySession) => void }) {
  const { triggerSessionSynthesis, retrySessionGeneration, retrySessionSynthesis, deleteSession } =
    useStoryPalStore()
  const jobState = getSessionJobState(session)
  const progress = session.story_state.synthesis_progress

  return (
    <div className="flex items-center justify-between rounded-lg border bg-card px-4 py-3">
      <div className="flex items-center gap-3 min-w-0">
        {jobState === 'generating' && <Loader2 className="h-4 w-4 animate-spin text-primary shrink-0" />}
        {jobState === 'needs_synthesis' && <FileText className="h-4 w-4 text-muted-foreground shrink-0" />}
        {jobState === 'synthesizing' && <Music className="h-4 w-4 text-primary shrink-0" />}
        {(jobState === 'gen_failed' || jobState === 'synth_failed') && (
          <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
        )}
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">{session.title}</p>
          {jobState === 'generating' && (
            <p className="text-xs text-muted-foreground">文字產生中...</p>
          )}
          {jobState === 'needs_synthesis' && (
            <p className="text-xs text-muted-foreground">故事已就緒</p>
          )}
          {jobState === 'synthesizing' && progress && (
            <div className="flex items-center gap-2 mt-1">
              <div className="h-1.5 w-32 rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full bg-primary transition-all"
                  style={{ width: `${(progress.completed / Math.max(progress.total, 1)) * 100}%` }}
                />
              </div>
              <span className="text-xs font-mono text-primary">
                {progress.completed}/{progress.total} 音段
              </span>
            </div>
          )}
          {jobState === 'gen_failed' && (
            <p className="text-xs text-destructive">文字生成失敗</p>
          )}
          {jobState === 'synth_failed' && (
            <p className="text-xs text-destructive">
              {session.story_state.synthesis_error === 'quota_exceeded'
                ? 'TTS 配額已用盡，明日重試'
                : '音訊合成失敗'}
            </p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0 ml-3">
        {jobState === 'needs_synthesis' && (
          <button
            onClick={() => { if (onReview) { onReview(session) } else { void triggerSessionSynthesis(session.id) } }}
            className="flex items-center gap-1 rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90"
          >
            <Eye className="h-3 w-3" /> 預覽 & 合成
          </button>
        )}
        {jobState === 'gen_failed' && (
          <>
            <button
              onClick={() => { void retrySessionGeneration(session.id) }}
              className="text-xs text-primary hover:underline"
            >
              重試
            </button>
            <button
              onClick={() => { void deleteSession(session.id) }}
              className="text-xs text-destructive hover:underline"
            >
              刪除
            </button>
          </>
        )}
        {jobState === 'synth_failed' && (
          <>
            {session.story_state.synthesis_error !== 'quota_exceeded' && (
              <button
                onClick={() => { void retrySessionSynthesis(session.id) }}
                className="text-xs text-primary hover:underline"
              >
                重試
              </button>
            )}
            <button
              onClick={() => { void deleteSession(session.id) }}
              className="text-xs text-destructive hover:underline"
            >
              刪除
            </button>
          </>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// StorySessionList
// =============================================================================

interface StorySessionListProps {
  /** Pre-filtered sessions to display */
  sessions: StorySession[]
  isLoading: boolean
  headerTitle: string
  headerIcon?: ReactNode
  newButtonLabel: string
  emptyMessage: string
  onNewStory: () => void
  onOpenSession: (session: StorySession) => void
  /** Whether to show job cards section (for static story mode) */
  showJobCards?: boolean
  /** Callback when clicking review on a job card */
  onReviewSession?: (session: StorySession) => void
}

export function StorySessionList({
  sessions,
  isLoading,
  headerTitle,
  newButtonLabel,
  emptyMessage,
  onNewStory,
  onOpenSession,
  showJobCards = false,
  onReviewSession,
}: StorySessionListProps) {
  const deleteSession = useStoryPalStore((s) => s.deleteSession)

  const jobSessions = showJobCards ? sessions.filter((s) => getSessionJobState(s) !== null) : []
  const readySessions = showJobCards
    ? sessions.filter((s) => getSessionJobState(s) === null)
    : sessions

  return (
    <div className="mx-auto max-w-7xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">{headerTitle}</h1>
        </div>
        <button
          onClick={onNewStory}
          className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow hover:bg-primary/90"
        >
          <Plus className="h-4 w-4" />
          {newButtonLabel}
        </button>
      </div>

      {/* Loading */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : (
        <>
          {/* Job cards section */}
          {jobSessions.length > 0 && (
            <div className="mb-6">
              <p className="text-sm font-medium text-muted-foreground mb-2">
                製作中 ({jobSessions.length})
              </p>
              <div className="space-y-2">
                {jobSessions.map((s) => (
                  <JobCard key={s.id} session={s} onReview={onReviewSession} />
                ))}
              </div>
            </div>
          )}

          {/* Separator */}
          {jobSessions.length > 0 && readySessions.length > 0 && (
            <div className="relative my-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t" />
              </div>
              <div className="relative flex justify-center">
                <span className="bg-background px-2 text-xs text-muted-foreground">可播放的故事</span>
              </div>
            </div>
          )}

          {/* Empty state */}
          {readySessions.length === 0 && jobSessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 space-y-4 rounded-lg border border-dashed">
              <BookOpen className="h-12 w-12 text-muted-foreground/40" />
              <p className="text-sm text-muted-foreground">{emptyMessage}</p>
            </div>
          ) : readySessions.length > 0 ? (
            /* Ready sessions grid */
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {readySessions.map((s) => {
                const date = new Date(s.started_at).toLocaleDateString('zh-TW')
                const characters = s.characters_config?.slice(0, 3) ?? []
                return (
                  <div
                    key={s.id}
                    className="group relative flex flex-col gap-3 rounded-xl border bg-card p-4 transition-shadow hover:shadow-md cursor-pointer"
                    onClick={() => onOpenSession(s)}
                  >
                    <p className="font-semibold truncate pr-8">{s.title}</p>

                    {characters.length > 0 && (
                      <div className="flex gap-1">
                        {characters.map((c) => (
                          <span
                            key={c.name}
                            className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary"
                          >
                            {c.name}
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="flex items-center justify-between mt-auto">
                      <span className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {date}
                      </span>
                      <span
                        className={cn(
                          'rounded-full px-2 py-0.5 text-xs font-medium',
                          s.status === 'completed'
                            ? 'bg-green-100 text-green-700'
                            : s.status === 'active'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-muted text-muted-foreground'
                        )}
                      >
                        {s.status === 'completed' ? '已完成' : s.status === 'active' ? '進行中' : '暫停'}
                      </span>
                    </div>

                    <button
                      onClick={(e) => { e.stopPropagation(); void deleteSession(s.id) }}
                      className="absolute right-3 top-3 hidden rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive group-hover:block"
                    >
                      ✕
                    </button>
                  </div>
                )
              })}
            </div>
          ) : null}
        </>
      )}
    </div>
  )
}
