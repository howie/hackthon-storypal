/**
 * Song Output
 * Feature: StoryPal — AI Interactive Story Companion
 *
 * Displays generated song lyrics and Suno prompt with copy-to-clipboard functionality.
 */

import { useCallback, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, Check, Copy, Loader2, Music } from 'lucide-react'
import type { SongContent } from '@/types/storypal'
import { cn } from '@/lib/utils'

interface SongOutputProps {
  songContent: SongContent | null
  isGenerating?: boolean
  error?: string | null
  onGenerate?: () => void
}

export function SongOutput({ songContent, isGenerating = false, error, onGenerate }: SongOutputProps) {
  const { t } = useTranslation('story')
  const [copiedField, setCopiedField] = useState<'lyrics' | 'suno_prompt' | null>(null)

  const handleCopy = useCallback(async (text: string, field: 'lyrics' | 'suno_prompt') => {
    await navigator.clipboard.writeText(text)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 1500)
  }, [])

  // ── Loading state ────────────────────────────────────────────────────────
  if (isGenerating) {
    return (
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('song.generating')}
        </div>
        <div className="mt-4 space-y-3">
          <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
          <div className="h-4 w-full animate-pulse rounded bg-muted" />
          <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
          <div className="h-4 w-5/6 animate-pulse rounded bg-muted" />
        </div>
      </div>
    )
  }

  // ── Error state ─────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-card p-6 text-center">
        <AlertTriangle className="mx-auto mb-2 h-8 w-8 text-destructive/70" />
        <p className="text-sm font-medium text-destructive">{error}</p>
        {onGenerate && (
          <button
            onClick={onGenerate}
            className="mt-3 rounded-lg border border-destructive/30 px-4 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10"
          >
            {t('common:actions.retry')}
          </button>
        )}
      </div>
    )
  }

  // ── Empty state ──────────────────────────────────────────────────────────
  if (!songContent) {
    return (
      <div className="rounded-lg border border-dashed bg-card p-6 text-center">
        <Music className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
        <p className="text-sm text-muted-foreground">{t('song.noSong')}</p>
        {onGenerate && (
          <button
            onClick={onGenerate}
            className="mt-3 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            {t('song.generateSong')}
          </button>
        )}
      </div>
    )
  }

  // ── Content display ──────────────────────────────────────────────────────
  return (
    <div className="space-y-4 rounded-lg border bg-card p-6">
      {/* Lyrics */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="flex items-center gap-2 text-sm font-semibold">
            <Music className="h-4 w-4 text-primary" />
            {t('song.lyrics')}
          </h3>
          <CopyButton
            copied={copiedField === 'lyrics'}
            onClick={() => handleCopy(songContent.lyrics, 'lyrics')}
            copiedLabel={t('song.copied')}
            copyLabel={t('song.copy')}
          />
        </div>
        <pre className="whitespace-pre-wrap rounded-md bg-muted/50 p-4 text-sm leading-relaxed">
          {songContent.lyrics}
        </pre>
      </div>

      {/* Suno Prompt */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold">Suno Prompt</h3>
          <CopyButton
            copied={copiedField === 'suno_prompt'}
            onClick={() => handleCopy(songContent.suno_prompt, 'suno_prompt')}
            copiedLabel={t('song.copied')}
            copyLabel={t('song.copy')}
          />
        </div>
        <div className="rounded-md bg-muted/50 p-4 font-mono text-xs leading-relaxed text-muted-foreground">
          {songContent.suno_prompt}
        </div>
      </div>
    </div>
  )
}

// ─── Copy Button ───────────────────────────────────────────────────────────

function CopyButton({ copied, onClick, copiedLabel, copyLabel }: { copied: boolean; onClick: () => void; copiedLabel: string; copyLabel: string }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-1 rounded px-2 py-1 text-xs transition-colors',
        copied
          ? 'text-green-600 dark:text-green-400'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
      )}
    >
      {copied ? (
        <>
          <Check className="h-3 w-3" />
          {copiedLabel}
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          {copyLabel}
        </>
      )}
    </button>
  )
}
