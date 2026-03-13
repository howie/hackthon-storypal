/**
 * TemplateBrowser
 * Shared component for browsing and selecting story templates.
 * Used by both StoryPage and StoryGamePage.
 */

import type { ReactNode } from 'react'
import { ArrowLeft, Sparkles } from 'lucide-react'
import { StoryTemplateCard } from './StoryTemplateCard'
import { useStoryPalStore } from '@/stores/storypalStore'
import type { StoryCategory, StoryTemplate } from '@/types/storypal'
import { STORY_CATEGORIES } from '@/types/storypal'
import { cn } from '@/lib/utils'

interface TemplateBrowserProps {
  onBack: () => void
  /** Slot for action buttons shown when a template is selected */
  actionButtons?: ReactNode
  /** Optional header action (e.g. "自訂故事" button) */
  headerAction?: ReactNode
  title?: string
  subtitle?: string
}

export function TemplateBrowser({
  onBack,
  actionButtons,
  headerAction,
  title = '選擇故事範本',
  subtitle = 'AI 故事陪伴 — 讓每個孩子都有專屬的說書人',
}: TemplateBrowserProps) {
  const templates = useStoryPalStore((s) => s.templates)
  const selectedTemplate = useStoryPalStore((s) => s.selectedTemplate)
  const isLoadingTemplates = useStoryPalStore((s) => s.isLoadingTemplates)
  const categoryFilter = useStoryPalStore((s) => s.categoryFilter)
  const selectTemplate = useStoryPalStore((s) => s.selectTemplate)
  const setCategoryFilter = useStoryPalStore((s) => s.setCategoryFilter)

  const filteredTemplates = categoryFilter
    ? templates.filter((t) => t.category === categoryFilter)
    : templates

  return (
    <div className="mx-auto max-w-7xl">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={onBack}
          className="mb-3 flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </button>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold">{title}</h1>
          </div>
          {headerAction}
        </div>
        <p className="text-muted-foreground">{subtitle}</p>
      </div>

      <div className="space-y-4">
        <div className="space-y-4">
          {/* Category filter */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setCategoryFilter(null)}
              className={cn(
                'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                !categoryFilter
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-accent'
              )}
            >
              全部
            </button>
            {(Object.entries(STORY_CATEGORIES) as [StoryCategory, { label: string; emoji: string }][]).map(
              ([key, { label, emoji }]) => (
                <button
                  key={key}
                  onClick={() => setCategoryFilter(key)}
                  className={cn(
                    'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                    categoryFilter === key
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:bg-accent'
                  )}
                >
                  {emoji} {label}
                </button>
              )
            )}
          </div>

          {/* Template grid */}
          {isLoadingTemplates ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : filteredTemplates.length === 0 ? (
            <div className="py-12 text-center text-sm text-muted-foreground">
              還沒有故事範本，敬請期待！
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2">
              {filteredTemplates.map((template: StoryTemplate) => (
                <StoryTemplateCard
                  key={template.id}
                  template={template}
                  isSelected={selectedTemplate?.id === template.id}
                  onSelect={selectTemplate}
                />
              ))}
            </div>
          )}

          {/* Action buttons */}
          {selectedTemplate && actionButtons && (
            <div className="sticky bottom-0 flex flex-wrap justify-center gap-3 border-t bg-background/80 py-4 backdrop-blur-sm">
              {actionButtons}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
