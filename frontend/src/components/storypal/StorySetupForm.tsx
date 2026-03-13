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
import { BookOpen, ChevronDown, GitFork, Loader2, Sparkles, User, Users } from 'lucide-react'
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

function getAgeHint(age: number): { label: string; description: string; color: string } {
  if (age <= 2)
    return {
      label: '小寶寶（1-2歲）',
      description: '極短句、重複節奏、擬聲詞，一件事的小故事',
      color: 'bg-pink-50 border-pink-200',
    }
  if (age <= 4)
    return {
      label: '幼幼班（3-4歲）',
      description: '短句、生活詞彙，簡單起因結果情節',
      color: 'bg-yellow-50 border-yellow-200',
    }
  if (age <= 6)
    return {
      label: '幼稚園（5-6歲）',
      description: '中等句長，有輕微懸念，基本邏輯因果',
      color: 'bg-green-50 border-green-200',
    }
  return {
    label: '小學低年級（7-8歲）',
    description: '較長段落，情節轉折，可引入道德思考',
    color: 'bg-blue-50 border-blue-200',
  }
}

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

// ─── Extra options ───────────────────────────────────────────────────────────

const EXTRA_OPTIONS: {
  key: string
  icon: string
  label: string
  description: string
  disabled?: boolean
}[] = [
  { key: 'qa', icon: '❓', label: '故事 Q&A', description: '針對故事內容的問答' },
  { key: 'song', icon: '🎵', label: '主題兒歌', description: '即將推出', disabled: true },
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
}

// ─── Component ───────────────────────────────────────────────────────────────

export function StorySetupForm({
  defaults,
  templates = [],
  selectedTemplate = null,
  onSelectTemplate,
  onSubmit,
  isLoading = false,
}: StorySetupFormProps) {
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

  const handleTemplateSelect = (t: StoryTemplate | null) => {
    onSelectTemplate?.(t)
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
      child_name: childName || '小朋友',
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
          <h2 className="text-lg font-semibold">故事設定</h2>
          <p className="text-sm text-muted-foreground">
            選擇故事風格、填入孩子的資訊，AI 將生成專屬故事
          </p>
        </div>

        {/* ── Template Selector (optional) ─────────────────────────────── */}
        {templates.length > 0 && (
          <div className="border-b pb-6">
            <label className="mb-2 block text-sm font-medium">故事風格範本</label>
            <p className="mb-2 text-xs text-muted-foreground">可選擇範本設定故事風格，或留空自訂</p>
            <div className="relative">
              <button
                type="button"
                onClick={() => setTemplateDropdownOpen((prev) => !prev)}
                className="flex w-full items-center justify-between rounded-md border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <span className={selectedTemplate ? 'text-foreground' : 'text-muted-foreground'}>
                  {selectedTemplate ? selectedTemplate.name : '不使用範本（自訂風格）'}
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
                    不使用範本（自訂風格）
                  </button>
                  {templates.map((t) => {
                    const cat = STORY_CATEGORIES[t.category]
                    return (
                      <button
                        type="button"
                        key={t.id}
                        onClick={() => handleTemplateSelect(t)}
                        className={cn(
                          'w-full px-3 py-2 text-left hover:bg-accent',
                          selectedTemplate?.id === t.id && 'bg-accent/50',
                        )}
                      >
                        <div className="flex items-center gap-2">
                          <span>{cat?.emoji}</span>
                          <span className="text-sm font-medium">{t.name}</span>
                          <span className="ml-auto text-xs text-muted-foreground">
                            {t.target_age_min}-{t.target_age_max} 歲
                          </span>
                        </div>
                        <p className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">{t.description}</p>
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
            孩子的名字
          </label>
          <p className="mb-2 text-xs text-muted-foreground">
            故事會直接用這個名字稱呼孩子，留空則使用「小朋友」
          </p>
          <input
            id="child-name"
            type="text"
            value={childName}
            onChange={(e) => setChildName(e.target.value)}
            placeholder="小朋友"
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* ── Age Slider ── FR-001 ──────────────────────────────────────── */}
        <div className="border-b pb-6">
          <div className="mb-2 flex items-center justify-between">
            <label htmlFor="age-slider" className="text-sm font-medium">
              孩子年齡
            </label>
            <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-sm font-medium text-primary">
              {age} 歲
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
            aria-label="孩子年齡"
            aria-valuemin={1}
            aria-valuemax={8}
            aria-valuenow={age}
            className="w-full accent-primary"
          />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>1歲</span>
            <span>8歲</span>
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
            希望孩子學會的事情
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
            placeholder="例如：自己穿室內拖、學會說謝謝..."
            rows={2}
            className="w-full resize-none rounded-md border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* ── Values Multi-Select ── FR-004 ────────────────────────────── */}
        <div className="border-b pb-6">
          <div className="mb-2">
            <label className="text-sm font-medium">希望融入的價值觀</label>
            <span className="ml-2 text-xs text-muted-foreground">
              可不選，系統會自動推斷
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
            <label className="text-sm font-medium">希望探索的情緒主題</label>
            <span className="ml-2 text-xs text-muted-foreground">
              可不選，系統會自動推斷
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
            孩子最喜歡的角色
          </label>
          {selectedTemplate && (
            <p className="mb-2 text-xs text-muted-foreground">
              填寫後會取代範本的主角，留空則使用範本原有角色
            </p>
          )}
          <input
            id="favorite-character"
            type="text"
            value={favoriteCharacter}
            onChange={(e) => setFavoriteCharacter(e.target.value)}
            placeholder="例如：超人力霸王、巧虎、佩佩豬..."
            className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
          />
        </div>

        {/* ── Voice Mode (moved up, right after child config) ─────────── */}
        <div className="border-b pb-6">
          <h3 className="mb-3 text-sm font-medium">角色配音模式</h3>
          <p className="mb-3 text-xs text-muted-foreground">
            系統會根據角色自動選配聲音
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
              <span className="text-sm font-medium">多角色配音</span>
              <span className="text-xs text-muted-foreground text-center">
                每個角色用各自的語音
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
              <span className="text-sm font-medium">旁白模式</span>
              <span className="text-xs text-muted-foreground text-center">
                全部用同一個語音朗讀
              </span>
            </button>
          </div>
        </div>

        {/* ── TTS Provider ────────────────────────────────────────────── */}
        <div className="border-b pb-6">
          <h3 className="mb-3 text-sm font-medium">語音引擎</h3>
          <p className="mb-3 text-xs text-muted-foreground">
            選擇語音合成引擎，影響語音品質與速度
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
              <span className="text-xs text-muted-foreground text-center">高品質語音</span>
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
              <span className="text-xs text-muted-foreground text-center">快速生成</span>
            </button>
          </div>
        </div>

        {/* ── Story Mode ───────────────────────────────────────────────── */}
        <div className="border-b pb-6">
          <h3 className="mb-3 text-sm font-medium">故事類型</h3>
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
              <span className="text-sm font-medium">故事產生</span>
              <span className="text-xs text-muted-foreground text-center">
                純線性故事，完整起承轉合
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
              <span className="text-sm font-medium">故事走向</span>
              <span className="text-xs text-muted-foreground text-center">
                含 A/B 選擇的互動故事
              </span>
            </button>
          </div>
        </div>

        {/* ── Extra Options ────────────────────────────────────────────── */}
        <div className="border-b pb-6">
          <h3 className="mb-3 text-sm font-medium">額外選項</h3>
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
                    即將推出
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
                故事準備中...
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                開始生成故事
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  )
}
