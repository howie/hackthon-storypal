/**
 * TutorPromptEditor — Collapsible panel for viewing/editing the Tutor system prompt.
 *
 * Allows parents to see how the AI prompt changes with age selection,
 * and optionally customise it before starting a session.
 */

import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TutorPromptEditorProps {
  systemPrompt: string
  onSystemPromptChange: (value: string) => void
  isEdited: boolean
  isOpen: boolean
  onToggleOpen: () => void
  onResetToDefault: () => void
  disabled: boolean
}

const MAX_PROMPT_LENGTH = 2000

export function TutorPromptEditor({
  systemPrompt,
  onSystemPromptChange,
  isEdited,
  isOpen,
  onToggleOpen,
  onResetToDefault,
  disabled,
}: TutorPromptEditorProps) {
  const charCount = systemPrompt.length
  const charPercentage = (charCount / MAX_PROMPT_LENGTH) * 100

  const handleChange = (value: string) => {
    if (value.length <= MAX_PROMPT_LENGTH) {
      onSystemPromptChange(value)
    }
  }

  return (
    <div className="border-b">
      {/* Collapsible header */}
      <button
        type="button"
        onClick={onToggleOpen}
        className="flex w-full items-center justify-between px-1 py-2 text-sm"
      >
        <div className="flex items-center gap-2">
          <ChevronDown
            className={cn(
              'h-4 w-4 text-muted-foreground transition-transform',
              !isOpen && '-rotate-90'
            )}
          />
          <span className="font-medium">系統提示詞</span>
          {isEdited && (
            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
              已修改
            </span>
          )}
        </div>
      </button>

      {/* Expandable content */}
      {isOpen && (
        <div className="space-y-2 px-1 pb-3">
          <textarea
            value={systemPrompt}
            onChange={(e) => handleChange(e.target.value)}
            disabled={disabled}
            rows={5}
            className="w-full resize-none rounded-md border bg-background px-3 py-2 text-sm leading-relaxed focus:border-primary focus:outline-none disabled:opacity-50"
            placeholder="載入中..."
          />
          <div className="flex items-center justify-between">
            <span
              className={cn(
                'text-xs',
                charPercentage >= 100
                  ? 'text-destructive'
                  : charPercentage >= 80
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-muted-foreground'
              )}
            >
              {charCount} / {MAX_PROMPT_LENGTH}
            </span>
            {isEdited && (
              <button
                type="button"
                onClick={onResetToDefault}
                disabled={disabled}
                className="text-xs text-muted-foreground underline hover:text-foreground disabled:opacity-50"
              >
                恢復預設
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
