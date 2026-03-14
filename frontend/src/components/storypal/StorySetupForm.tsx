/**
 * Story Setup Form — Unified story creation
 * Feature: StoryPal — AI Interactive Story Companion
 *
 * Merged flow: optional template selection + child personalisation + voice/story mode.
 * Parents configure everything in one page, then generate the story directly.
 *
 * Voice selection is removed — the backend auto-assigns voices from a pool
 * based on character names (multi_role) or uses a single narrator (single_role).
 */

import { useState } from 'react'
import { BookOpen, ChevronDown, GitFork, Globe, Loader2, Sparkles, User, Users } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type {
  ChildConfig,
  EmotionKey,
  EmotionOption,
  StoryDefaultsResponse,
  StoryTemplate,
  ValueKey,
  ValueOption,
} from '@/types/storypal'
import { STORY_CATEGORIES } from '@/types/storypal'
import { cn } from '@/lib/utils'

// ─── Exported types ──────────────────────────────────────────────────────────

export type VoiceMode = 'multi_role' | 'single_role'
export type StoryMode = 'linear' | 'branching'

// ─── Fallback defaults (used when API hasn't loaded yet) ─────────────────────

const FALLBACK_LEARNING_SCENARIOS = [
  '自己穿室內拖',
  '自己刷牙',
  '溜滑梯排隊禮讓',
  '說請和謝謝',
  '自己整理玩具',
  '安靜等待輪到自己',
]

const FALLBACK_VALUES: ValueOption[] = [
  { key: 'empathy_care', label: '同理心與關懷' },
  { key: 'honesty_responsibility', label: '誠實與責任感' },
  { key: 'respect_cooperation', label: '尊重與合作' },
  { key: 'curiosity_exploration', label: '好奇心與探索' },
  { key: 'self_management', label: '自主管理與自信' },
  { key: 'resilience', label: '彈性與堅持' },
]

const FALLBACK_EMOTIONS: EmotionOption[] = [
  { key: 'happiness', label: '快樂/高興' },
  { key: 'anger', label: '生氣/憤怒' },
  { key: 'sadness', label: '悲傷/難過' },
  { key: 'fear', label: '害怕/恐懼' },
  { key: 'surprise', label: '驚訝' },
  { key: 'disgust', label: '厭惡/討厭' },
  { key: 'pride', label: '驕傲' },
  { key: 'shame_guilt', label: '羞愧/罪惡感' },
  { key: 'jealousy', label: '嫉妒' },
]

// ─── Props ───────────────────────────────────────────────────────────────────

interface StorySetupFormProps {
  defaults?: StoryDefaultsResponse | null
  templates?: StoryTemplate[]
  selectedTemplate?: StoryTemplate | null
  onSelectTemplate?: (t: StoryTemplate | null) => void
  onSubmit: (
    config: ChildConfig,
    voiceMode: VoiceMode,
    storyMode: StoryMode,
    extras: string[],
    ttsProvider?: string,
  ) => void
  isLoading?: boolean
  contentLanguage?: string
  onContentLanguageChange?: (lang: string) => void
}

// ─── Component ───────────────────────────────────────────────────────────────

export function StorySetupForm({
  defaults,
  templates = [],
  selectedTemplate = null,
  onSelectTemplate,
  onSubmit,
  isLoading = false,
  contentLanguage = 'zh-TW',
  onContentLanguageChange,
}: StorySetupFormProps) {
  const { t } = useTranslation('story')

  // Resolve defaults with fallbacks
  const learningScenarios = defaults?.default_learning_scenarios ?? FALLBACK_LEARNING_SCENARIOS
  const valueOptions = defaults?.values ?? FALLBACK_VALUES
  const emotionOptions = defaults?.emotions ?? FALLBACK_EMOTIONS

  const [age, setAge] = useState(4)
  const [childName, setChildName] = useState('')
  const [learningGoals, setLearningGoals] = useState('')
  const [selectedValues, setSelectedValues] = useState<ValueKey[]>([])
  const [selectedEmotions, setSelectedEmotions] = useState<EmotionKey[]>([])
  const [favoriteCharacter, setFavoriteCharacter] = useState('')
  const [voiceMode, setVoiceMode] = useState<VoiceMode>('multi_role')
  const [storyMode, setStoryMode] = useState<StoryMode>('linear')
  const [selectedExtras, setSelectedExtras] = useState<Record<string, boolean>>({})
  const [ttsProvider, setTtsProvider] = useState<'gemini-pro' | 'gemini-flash'>('gemini-pro')
  const [templateDropdownOpen, setTemplateDropdownOpen] = useState(false)

  // ── Age hint ───────────────────────────────────────────────────────────
  function getAgeHint(a: number): { label: string; description: string; color: string } {
    if (a <= 2)
      return {
        label: t('ageHint.baby'),
        description: t('ageHint.babyDesc'),
        color: 'bg-pink-50 border-pink-200',
      }
    if (a <= 4)
      return {
        label: t('ageHint.toddler'),
        description: t('ageHint.toddlerDesc'),
        color: 'bg-yellow-50 border-yellow-200',
      }
    if (a <= 6)
      return {
        label: t('ageHint.preschool'),
        description: t('ageHint.preschoolDesc'),
        color: 'bg-green-50 border-green-200',
      }
    return {
      label: t('ageHint.elementary'),
      description: t('ageHint.elementaryDesc'),
      color: 'bg-blue-50 border-blue-200',
    }
  }

  // ── Extra options ──────────────────────────────────────────────────────
  const EXTRA_OPTIONS: {
    key: string
    icon: string
    label: string
    description: string
    disabled?: boolean
  }[] = [
    { key: 'qa', icon: '❓', label: t('setup.storyQA'), description: t('setup.storyQADesc') },
    { key: 'song', icon: '🎵', label: t('setup.themeSong'), description: t('setup.themeSongDesc'), disabled: true },
  ]

  // ── Handlers ─────────────────────────────────────────────────────────────

  const toggleScenarioChip = (scenario: string) => {
    setLearningGoals((prev) => {
      const parts = prev
        .split('、')
        .map((s) => s.trim())
        .filter(Boolean)
      if (parts.includes(scenario)) {
        return parts.filter((s) => s !== scenario).join('、')
      }
      return [...parts, scenario].join('、')
    })
  }

  const isScenarioSelected = (scenario: string) => {
    return learningGoals
      .split('、')
      .map((s) => s.trim())
      .includes(scenario)
  }

  const toggleValue = (key: ValueKey) => {
    setSelectedValues((prev) =>
      prev.includes(key) ? prev.filter((v) => v !== key) : [...prev, key]
    )
  }

  const toggleEmotion = (key: EmotionKey) => {
    setSelectedEmotions((prev) =>
      prev.includes(key) ? prev.filter((e) => e !== key) : [...prev, key]
    )
  }

  const handleTemplateSelect = (tmpl: StoryTemplate | null) => {
    onSelectTemplate?.(tmpl)
    setTemplateDropdownOpen(false)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const childConfig: ChildConfig = {
      age,
      learning_goals: learningGoals,
      selected_values: selectedValues,
      selected_emotions: selectedEmotions,
      favorite_character: favoriteCharacter,
      child_name: childName || t('setup.childNamePlaceholder'),
    }
    const extras = Object.keys(selectedExtras).filter((k) => selectedExtras[k])
    onSubmit(childConfig, voiceMode, storyMode, extras, ttsProvider)
  }

  // ── Render ───────────────────────────────────────────────────────────────

  return (
    <form
      onSubmit={handleSubmit}
      className="mx-auto max-w-2xl rounded-lg border bg-card p-6"
    >
      <div className="space-y-6">
        {/* ── Title ─────────────────────────────────────────────────────── */}
        <div>
          <h2 className="text-lg font-semibold">{t('setup.title')}</h2>
          <p className="text-sm text-muted-foreground">
            {t('setup.subtitle')}
          </p>
        </div>

        {/* ── Content Language ────────────────────────────────────────── */}
        <div className="border-b pb-6">
          <h3 className="mb-2 text-sm font-medium flex items-center gap-1.5">
            <Globe className="h-4 w-4" />
            {t('setup.contentLanguage')}
          </h3>
          <p className="mb-3 text-xs text-muted-foreground">
            {t('setup.contentLanguageHint')}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => onContentLanguageChange?.('zh-TW')}
              className={cn(
                'flex flex-col items-center gap-1.5 rounded-xl border-2 p-3 transition-all',
                contentLanguage === 'zh-TW'
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-muted-foreground/30'
              )}
            >
              <span className="text-sm font-medium">{t('setup.chinese')}</span>
              <span className="text-xs text-muted-foreground">{t('setup.chineseDesc')}</span>
            </button>
            <button
              type="button"
              onClick={() => onContentLanguageChange?.('en')}
              className={cn(
                'flex flex-col items-center gap-1.5 rounded-xl border-2 p-3 transition-all',
                contentLanguage === 'en'
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-muted-foreground/30'
              )}
            >
              <span className="text-sm font-medium">{t('setup.english')}</span>
              <span className="text-xs text-muted-foreground">{t('setup.englishDesc')}</span>
            </button>
          </div>
        </div>

        {/* ── Template Selector (optional) ─────────────────────────────── */}
        {templates.length > 0 && (
          <div className="border-b pb-6">
            <label className="mb-2 block text-sm font-medium">{t('setup.templateLabel')}</label>
            <p className="mb-2 text-xs text-muted-foreground">{t('setup.templateHint')}</p>
            <div className="relative">
              <button
                type="button"
                onClick={() => setTemplateDropdownOpen((prev) => !prev)}
                className="flex w-full items-center justify-between rounded-md border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <span className={selectedTemplate ? 'text-foreground' : 'text-muted-foreground'}>
                  {selectedTemplate ? selectedTemplate.name : t('setup.noTemplate')}
                </span>
                <ChevronDown className={cn('h-4 w-4 text-muted-foreground transition-transform', templateDropdownOpen && 'rotate-180')} />
              </button>
              {templateDropdownOpen && (
                <>
                <div className="fixed inset-0 z-[9]" onClick={() => setTemplateDropdownOpen(false)} />
                <div className="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded-md border bg-popover shadow-lg">
                  <button
                    type="button"
                    onClick={() => handleTemplateSelect(null)}
                    className={cn(
                      'w-full px-3 py-2 text-left text-sm hover:bg-accent',
                      !selectedTemplate && 'bg-accent/50 font-medium',
                    )}
                  >
                    {t('setup.noTemplate')}
                  </button>
                  {templates.map((tmpl) => {
                    const cat = STORY_CATEGORIES[tmpl.category]
                    return (
                      <button
                        type="button"
                        key={tmpl.id}
                        onClick={() => handleTemplateSelect(tmpl)}
                        className={cn(
                          'w-full px-3 py-2 text-left hover:bg-accent',
                          selectedTemplate?.id === tmpl.id && 'bg-accent/50',
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <span>{cat?.emoji}</span>
                          <span className="text-sm font-medium">{tmpl.name}</span>
                          <span className="ml-auto text-xs text-muted-foreground">
                            {tmpl.target_age_min}-{tmpl.target_age_max} {t('setup.ageYears')}
                          </span>
                        </div>
                        <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{tmpl.description}</p>
                      </button>
                    )
                  })}
                </div>
                </>
              )}
            </div>
            {/* Template preview */}
            {selectedTemplate && (
              <div className="mt-3 rounded-md border bg-muted/30 p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span>{STORY_CATEGORIES[selectedTemplate.category]?.emoji}</span>
                  <span className="text-sm font-medium">{selectedTemplate.name}</span>
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{selectedTemplate.description}</p>
                {selectedTemplate.characters.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {selectedTemplate.characters.map((c) => (
                      <span
                        key={c.name}
                        className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary"
                      >
                        {c.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── Child Name ───────────────────────────────────────────────── */}
        <div className="border-b pb-6">
          <label htmlFor="child-name" className="mb-1 block text-sm font-medium">
            {t('setup.childName')}
          </label>
          <p className="mb-2 text-xs text-muted-foreground">
            {t('setup.childNameHint')}
          </p>
          <input
            id="child-name"
            type="text"
            value={childName}
            onChange={(e) => setChildName(e.target.value)}
            placeholder={t('setup.childNamePlaceholder')}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* ── Age Slider ── FR-001 ──────────────────────────────────────── */}
        <div className="border-b pb-6">
          <div className="mb-2 flex items-center justify-between">
            <label htmlFor="age-slider" className="text-sm font-medium">
              {t('setup.childAge')}
            </label>
            <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-sm font-medium text-primary">
              {age} {t('setup.ageYears')}
            </span>
          </div>
          <input
            id="age-slider"
            type="range"
            min={1}
            max={8}
            step={1}
            value={age}
            onChange={(e) => setAge(Number(e.target.value))}
            aria-label={t('setup.childAge')}
            aria-valuemin={1}
            aria-valuemax={8}
            aria-valuenow={age}
            className="w-full accent-primary"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>1{t('setup.ageYears')}</span>
            <span>8{t('setup.ageYears')}</span>
          </div>
          {/* Age hint box — shows how age affects story complexity */}
          {(() => {
            const hint = getAgeHint(age)
            return (
              <div className={`mt-2 rounded-md border px-3 py-2 text-xs ${hint.color}`}>
                <span className="font-medium">{hint.label}</span>
                <span className="ml-2 text-muted-foreground">{hint.description}</span>
              </div>
            )
          })()}
        </div>

        {/* ── Learning Goals ── FR-002, FR-003 ─────────────────────────── */}
        <div className="border-b pb-6">
          <label htmlFor="learning-goals" className="mb-2 block text-sm font-medium">
            {t('setup.learningGoals')}
          </label>
          <div className="mb-2 flex flex-wrap gap-2">
            {learningScenarios.map((scenario) => (
              <button
                key={scenario}
                type="button"
                onClick={() => toggleScenarioChip(scenario)}
                role="checkbox"
                aria-checked={isScenarioSelected(scenario)}
                className={cn(
                  'cursor-pointer rounded-full border px-3 py-1.5 text-xs transition-colors',
                  isScenarioSelected(scenario)
                    ? 'border-primary/30 bg-primary/10 text-primary'
                    : 'border-transparent bg-muted text-muted-foreground hover:bg-accent'
                )}
              >
                {scenario}
              </button>
            ))}
          </div>
          <textarea
            id="learning-goals"
            value={learningGoals}
            onChange={(e) => setLearningGoals(e.target.value)}
            placeholder={t('setup.learningGoalsPlaceholder')}
            rows={2}
            className="w-full resize-none rounded-md border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* ── Values Multi-Select ── FR-004 ────────────────────────────── */}
        <div className="border-b pb-6">
          <div className="mb-2">
            <label className="text-sm font-medium">{t('setup.values')}</label>
            <span className="ml-2 text-xs text-muted-foreground">
              {t('setup.valuesHint')}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {valueOptions.map((v) => (
              <button
                key={v.key}
                type="button"
                onClick={() => toggleValue(v.key)}
                role="checkbox"
                aria-checked={selectedValues.includes(v.key)}
                className={cn(
                  'cursor-pointer rounded-full border px-3 py-1.5 text-xs transition-colors',
                  selectedValues.includes(v.key)
                    ? 'border-primary/30 bg-primary/10 text-primary'
                    : 'border-transparent bg-muted text-muted-foreground hover:bg-accent'
                )}
              >
                {v.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Emotions Multi-Select ── FR-005 ──────────────────────────── */}
        <div className="border-b pb-6">
          <div className="mb-2">
            <label className="text-sm font-medium">{t('setup.emotions')}</label>
            <span className="ml-2 text-xs text-muted-foreground">
              {t('setup.emotionsHint')}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {emotionOptions.map((e) => (
              <button
                key={e.key}
                type="button"
                onClick={() => toggleEmotion(e.key)}
                role="checkbox"
                aria-checked={selectedEmotions.includes(e.key)}
                className={cn(
                  'cursor-pointer rounded-full border px-3 py-1.5 text-xs transition-colors',
                  selectedEmotions.includes(e.key)
                    ? 'border-primary/30 bg-primary/10 text-primary'
                    : 'border-transparent bg-muted text-muted-foreground hover:bg-accent'
                )}
              >
                {e.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Favorite Character ── FR-006 ─────────────────────────────── */}
        <div className="border-b pb-6">
          <label htmlFor="favorite-character" className="mb-1 block text-sm font-medium">
            {t('setup.favoriteCharacter')}
          </label>
          {selectedTemplate && (
            <p className="mb-2 text-xs text-muted-foreground">
              {t('setup.favoriteCharacterTemplateHint')}
            </p>
          )}
          <input
            id="favorite-character"
            type="text"
            value={favoriteCharacter}
            onChange={(e) => setFavoriteCharacter(e.target.value)}
            placeholder={t('setup.favoriteCharacterPlaceholder')}
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* ── Voice Mode (moved up, right after child config) ─────────── */}
        <div className="border-b pb-6">
          <h3 className="mb-3 text-sm font-medium">{t('setup.voiceMode')}</h3>
          <p className="mb-3 text-xs text-muted-foreground">
            {t('setup.voiceModeHint')}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setVoiceMode('multi_role')}
              className={cn(
                'flex flex-col items-center gap-2 rounded-xl border-2 p-4 transition-all',
                voiceMode === 'multi_role'
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-muted-foreground/30'
              )}
            >
              <Users className="h-6 w-6 text-primary" />
              <span className="text-sm font-medium">{t('setup.multiRole')}</span>
              <span className="text-xs text-muted-foreground text-center">
                {t('setup.multiRoleDesc')}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setVoiceMode('single_role')}
              className={cn(
                'flex flex-col items-center gap-2 rounded-xl border-2 p-4 transition-all',
                voiceMode === 'single_role'
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-muted-foreground/30'
              )}
            >
              <User className="h-6 w-6 text-primary" />
              <span className="text-sm font-medium">{t('setup.singleRole')}</span>
              <span className="text-xs text-muted-foreground text-center">
                {t('setup.singleRoleDesc')}
              </span>
            </button>
          </div>
        </div>

        {/* ── TTS Provider ────────────────────────────────────────────── */}
        <div className="border-b pb-6">
          <h3 className="mb-3 text-sm font-medium">{t('setup.ttsEngine')}</h3>
          <p className="mb-3 text-xs text-muted-foreground">
            {t('setup.ttsEngineHint')}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setTtsProvider('gemini-pro')}
              className={cn(
                'flex flex-col items-center gap-1.5 rounded-xl border-2 p-3 transition-all',
                ttsProvider === 'gemini-pro'
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-muted-foreground/30'
              )}
            >
              <span className="text-sm font-medium">Gemini Pro</span>
              <span className="text-xs text-muted-foreground text-center">{t('setup.highQuality')}</span>
            </button>
            <button
              type="button"
              onClick={() => setTtsProvider('gemini-flash')}
              className={cn(
                'flex flex-col items-center gap-1.5 rounded-xl border-2 p-3 transition-all',
                ttsProvider === 'gemini-flash'
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-muted-foreground/30'
              )}
            >
              <span className="text-sm font-medium">Gemini Flash</span>
              <span className="text-xs text-muted-foreground text-center">{t('setup.fastGeneration')}</span>
            </button>
          </div>
        </div>

        {/* ── Story Mode ───────────────────────────────────────────────── */}
        <div className="border-b pb-6">
          <h3 className="mb-3 text-sm font-medium">{t('setup.storyType')}</h3>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setStoryMode('linear')}
              className={cn(
                'flex flex-col items-center gap-2 rounded-xl border-2 p-4 transition-all',
                storyMode === 'linear'
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-muted-foreground/30'
              )}
            >
              <BookOpen className="h-6 w-6 text-primary" />
              <span className="text-sm font-medium">{t('setup.linearStory')}</span>
              <span className="text-xs text-muted-foreground text-center">
                {t('setup.linearStoryDesc')}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setStoryMode('branching')}
              className={cn(
                'flex flex-col items-center gap-2 rounded-xl border-2 p-4 transition-all',
                storyMode === 'branching'
                  ? 'border-primary bg-primary/5'
                  : 'border-border hover:border-muted-foreground/30'
              )}
            >
              <GitFork className="h-6 w-6 text-primary" />
              <span className="text-sm font-medium">{t('setup.branchingStory')}</span>
              <span className="text-xs text-muted-foreground text-center">
                {t('setup.branchingStoryDesc')}
              </span>
            </button>
          </div>
        </div>

        {/* ── Extra Options ────────────────────────────────────────────── */}
        <div className="border-b pb-6">
          <h3 className="mb-3 text-sm font-medium">{t('setup.extraOptions')}</h3>
          <div className="space-y-2">
            {EXTRA_OPTIONS.map((opt) => (
              <label
                key={opt.key}
                className={cn(
                  'flex items-center gap-3 rounded-lg border p-3 transition-colors',
                  opt.disabled
                    ? 'cursor-not-allowed opacity-50'
                    : 'cursor-pointer hover:bg-accent/50',
                  selectedExtras[opt.key] && 'border-primary bg-primary/5',
                )}
              >
                <input
                  type="checkbox"
                  checked={!!selectedExtras[opt.key]}
                  onChange={() =>
                    setSelectedExtras((prev) => ({ ...prev, [opt.key]: !prev[opt.key] }))
                  }
                  disabled={opt.disabled}
                  className="h-4 w-4 rounded border-gray-300 text-primary accent-primary"
                />
                <span className="text-base">{opt.icon}</span>
                <div>
                  <span className="text-sm font-medium">{opt.label}</span>
                  <p className="text-xs text-muted-foreground">{opt.description}</p>
                </div>
                {opt.disabled && (
                  <span className="ml-auto rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                    {t('setup.comingSoon')}
                  </span>
                )}
              </label>
            ))}
          </div>
        </div>

        {/* ── Submit Button ────────────────────────────────────────────── */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isLoading}
            aria-busy={isLoading}
            className="flex items-center gap-2 rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground shadow-lg transition-all hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('setup.generating')}
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                {t('setup.generateStory')}
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  )
}
