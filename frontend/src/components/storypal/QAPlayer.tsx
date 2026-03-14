/**
 * QA Player
 * Feature: StoryPal — AI Interactive Story Companion
 *
 * Interactive Q&A player with SVG countdown timer, hints, and encouragement.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { AlertTriangle, CheckCircle2, HelpCircle, Lightbulb, Loader2, MessageCircle } from 'lucide-react'
import type { QAContent } from '@/types/storypal'
import { cn } from '@/lib/utils'

interface QAPlayerProps {
  qaContent: QAContent | null
  isGenerating?: boolean
  error?: string | null
  onGenerate?: () => void
}

export function QAPlayer({ qaContent, isGenerating = false, error, onGenerate }: QAPlayerProps) {
  const { t } = useTranslation('story')
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showHint, setShowHint] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [isTimerRunning, setIsTimerRunning] = useState(false)
  const [isCompleted, setIsCompleted] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const timeoutSeconds = qaContent?.timeout_seconds ?? 5
  const currentQuestion = qaContent?.questions[currentIndex]
  const totalQuestions = qaContent?.questions.length ?? 0

  // ── Timer logic ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isTimerRunning || countdown <= 0) return

    timerRef.current = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          setIsTimerRunning(false)
          setShowHint(true)
          if (timerRef.current) clearInterval(timerRef.current)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [isTimerRunning, countdown])

  const startQuestion = useCallback(() => {
    setShowHint(false)
    setCountdown(timeoutSeconds)
    setIsTimerRunning(true)
  }, [timeoutSeconds])

  // Start timer when question changes
  useEffect(() => {
    if (qaContent && !isCompleted) {
      startQuestion()
    }
  }, [currentIndex, qaContent, isCompleted, startQuestion])

  const handleNext = useCallback(() => {
    setIsTimerRunning(false)
    if (timerRef.current) clearInterval(timerRef.current)

    if (currentIndex < totalQuestions - 1) {
      setCurrentIndex((prev) => prev + 1)
      setShowHint(false)
    } else {
      setIsCompleted(true)
    }
  }, [currentIndex, totalQuestions])

  // ── Loading state ────────────────────────────────────────────────────────
  if (isGenerating) {
    return (
      <div className="rounded-lg border bg-card p-6">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('qa.generating')}
        </div>
        <div className="mt-4 space-y-3">
          <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />
          <div className="h-4 w-full animate-pulse rounded bg-muted" />
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
  if (!qaContent) {
    return (
      <div className="rounded-lg border border-dashed bg-card p-6 text-center">
        <HelpCircle className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
        <p className="text-sm text-muted-foreground">{t('qa.noQA')}</p>
        {onGenerate && (
          <button
            onClick={onGenerate}
            className="mt-3 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            {t('qa.generateQA')}
          </button>
        )}
      </div>
    )
  }

  // ── Completed state ──────────────────────────────────────────────────────
  if (isCompleted) {
    return (
      <div className="rounded-lg border bg-card p-6 text-center">
        <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-green-500" />
        <p className="mb-4 text-sm leading-relaxed text-muted-foreground">
          {qaContent.closing}
        </p>
        <button
          onClick={() => {
            setCurrentIndex(0)
            setIsCompleted(false)
            setShowHint(false)
          }}
          className="rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
        >
          {t('qa.playAgain')}
        </button>
      </div>
    )
  }

  // ── Question display ─────────────────────────────────────────────────────
  return (
    <div className="rounded-lg border bg-card p-6">
      {/* Progress */}
      <div className="mb-4 flex items-center justify-between text-xs text-muted-foreground">
        <span>
          {t('qa.question')} {currentIndex + 1} / {totalQuestions}
        </span>
        <div className="flex gap-1">
          {qaContent.questions.map((_, i) => (
            <div
              key={i}
              className={cn(
                'h-1.5 w-6 rounded-full',
                i < currentIndex ? 'bg-green-500' : i === currentIndex ? 'bg-primary' : 'bg-muted'
              )}
            />
          ))}
        </div>
      </div>

      {/* Timer + Question */}
      <div className="flex items-start gap-4">
        {/* SVG Countdown Ring */}
        <div className="relative shrink-0">
          <svg className="h-14 w-14 -rotate-90" viewBox="0 0 56 56">
            <circle
              cx="28"
              cy="28"
              r="24"
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              className="text-muted"
            />
            <circle
              cx="28"
              cy="28"
              r="24"
              fill="none"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 24}
              strokeDashoffset={2 * Math.PI * 24 * (1 - countdown / timeoutSeconds)}
              className={cn(
                'transition-all duration-1000',
                countdown > 2 ? 'text-primary' : 'text-amber-500'
              )}
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-sm font-bold">
            {countdown}
          </span>
        </div>

        {/* Question text */}
        <div className="flex-1">
          <p className="text-sm font-medium leading-relaxed">
            {currentQuestion?.question}
          </p>
        </div>
      </div>

      {/* Hint */}
      {showHint && currentQuestion && (
        <div className="mt-4 flex items-start gap-2 rounded-md bg-amber-50 p-3 dark:bg-amber-950/30">
          <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
          <p className="text-xs text-amber-700 dark:text-amber-400">
            {currentQuestion.hint}
          </p>
        </div>
      )}

      {/* Encouragement + Next */}
      <div className="mt-4 flex items-center justify-between">
        {showHint && currentQuestion && (
          <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
            <MessageCircle className="h-3.5 w-3.5" />
            {currentQuestion.encouragement}
          </div>
        )}
        <button
          onClick={handleNext}
          className="ml-auto rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
        >
          {currentIndex < totalQuestions - 1 ? t('qa.nextQuestion') : t('qa.done')}
        </button>
      </div>
    </div>
  )
}
