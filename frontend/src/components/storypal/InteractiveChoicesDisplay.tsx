/**
 * Interactive Choices Display
 * Feature: StoryPal — AI Interactive Story Companion
 *
 * Displays generated interactive choice nodes with branching story paths.
 */

import { useState } from 'react'
import { AlertTriangle, ChevronDown, ChevronRight, Loader2, Theater } from 'lucide-react'
import type { ChoiceNode, InteractiveChoicesContent } from '@/types/storypal'
import { cn } from '@/lib/utils'

interface InteractiveChoicesDisplayProps {
  choicesContent: InteractiveChoicesContent | null
  isGenerating?: boolean
  error?: string | null
  onGenerate?: () => void
}

/** Highlight [emotion] markers in text */
function HighlightedText({ text }: { text: string }) {
  const parts = text.split(/(\[[^\]]+\])/)
  return (
    <>
      {parts.map((part, i) =>
        /^\[.+\]$/.test(part) ? (
          <span key={i} className="font-medium text-primary/60">
            {part}
          </span>
        ) : (
          <span key={i}>{part}</span>
        )
      )}
    </>
  )
}

/** Extract continuation entries from a ChoiceNode */
function getContinuations(node: ChoiceNode): { option: string; text: string }[] {
  return Object.entries(node)
    .filter(([key]) => key.startsWith('continuation_'))
    .map(([key, value]) => ({
      option: key.replace('continuation_', ''),
      text: value as string,
    }))
}

export function InteractiveChoicesDisplay({
  choicesContent,
  isGenerating = false,
  error,
  onGenerate,
}: InteractiveChoicesDisplayProps) {
  // ── Loading state ────────────────────────────────────────────────────────
  if (isGenerating) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center">
        <div className="flex items-center justify-center gap-2 text-sm font-medium text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          正在設計故事走向互動...
        </div>
        <div className="mx-auto mt-4 h-2 w-2/3 animate-pulse rounded-full bg-gradient-to-r from-primary/20 via-primary/40 to-primary/20" />
        <p className="mt-3 text-xs text-muted-foreground">
          孩子可以選擇不同走向，所有結局都是正向的
        </p>
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
            重試
          </button>
        )}
      </div>
    )
  }

  // ── Empty state ──────────────────────────────────────────────────────────
  if (!choicesContent) {
    return (
      <div className="rounded-lg border border-dashed p-8 text-center">
        <Theater className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
        <p className="text-sm text-muted-foreground">還沒有生成互動選擇腳本</p>
        <p className="text-xs text-muted-foreground">
          AI 會在故事中插入 3-4 個選擇節點
        </p>
        {onGenerate && (
          <button
            onClick={onGenerate}
            className="mt-3 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            生成互動腳本
          </button>
        )}
      </div>
    )
  }

  // ── Content display ──────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Script */}
      <div>
        <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
          <span>📜</span> 互動故事底稿
        </h3>
        <div className="rounded-lg border bg-muted/30 p-4">
          <p className="whitespace-pre-wrap text-sm leading-relaxed">
            <HighlightedText text={choicesContent.script} />
          </p>
        </div>
      </div>

      {/* Choice Nodes */}
      <div>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
          <span>🎯</span> 互動選擇節點（共 {choicesContent.choice_nodes.length} 個）
        </h3>
        <div className="space-y-3">
          {choicesContent.choice_nodes.map((node) => (
            <ChoiceNodeCard key={node.order} node={node} />
          ))}
        </div>
      </div>

      {/* Generated at */}
      <p className="text-right text-xs text-muted-foreground">
        生成時間：{new Date(choicesContent.generated_at).toLocaleString('zh-TW')}
      </p>
    </div>
  )
}

// ─── Choice Node Card ──────────────────────────────────────────────────────

function ChoiceNodeCard({ node }: { node: ChoiceNode }) {
  const [expanded, setExpanded] = useState(false)
  const continuations = getContinuations(node)

  return (
    <div className="overflow-hidden rounded-lg border bg-card">
      {/* Header */}
      <div className="flex items-center justify-between bg-muted/50 px-4 py-2 text-xs font-semibold text-muted-foreground">
        <span>節點 {node.order}</span>
        <span>⏱️ {node.timeout_seconds} 秒</span>
      </div>

      {/* Context */}
      {node.context && (
        <p className="px-4 pt-3 text-sm italic text-muted-foreground">
          {node.context}
        </p>
      )}

      {/* Prompt */}
      <div className="mx-4 mt-2 rounded-lg border border-primary/20 bg-primary/5 p-3">
        <p className="text-sm font-medium">
          <HighlightedText text={node.prompt} />
        </p>
      </div>

      {/* Options */}
      <div className="mt-3 flex flex-wrap items-center gap-2 px-4">
        <span className="mr-1 text-xs text-muted-foreground">選項:</span>
        {node.options.map((opt) => (
          <span
            key={opt}
            className="rounded-full bg-primary/10 px-3 py-1 text-sm font-medium text-primary"
          >
            {opt}
          </span>
        ))}
      </div>

      {/* Timeout hint */}
      <div className="mt-2 px-4">
        <p className="text-xs text-muted-foreground">
          ⏱️ 超時提示（{node.timeout_seconds} 秒後）:
        </p>
        <p className="mt-0.5 text-sm text-amber-700 dark:text-amber-300">
          {node.timeout_hint}
        </p>
      </div>

      {/* Continuations (collapsible) */}
      {continuations.length > 0 && (
        <div className="mt-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex w-full items-center gap-1 px-4 py-2 text-xs font-medium text-primary hover:underline"
          >
            {expanded ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
            {expanded ? '收起分支結果' : '展開查看分支結果'}
          </button>
          {expanded && (
            <div className="mx-4 mb-3 space-y-0 rounded-lg border bg-muted/20 p-3">
              {continuations.map((c, i) => (
                <div
                  key={c.option}
                  className={cn(i > 0 && 'border-t pt-2', i > 0 && 'mt-2')}
                >
                  <span className="font-medium text-primary">{c.option}</span>
                  <span className="mx-1 text-muted-foreground">→</span>
                  <span className="text-sm">
                    <HighlightedText text={c.text} />
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Bottom padding when no continuations */}
      {continuations.length === 0 && <div className="pb-3" />}
    </div>
  )
}
