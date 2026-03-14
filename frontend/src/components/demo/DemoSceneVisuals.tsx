/**
 * Mock visual components for each demo scene.
 * These render lightweight representations of the actual app pages,
 * without needing real data or API connections.
 */

import { BookOpen, Gamepad2, Sparkles, Play, Pause, SkipForward, Volume2, Mic, Download, MessageCircle, ChevronRight } from 'lucide-react'
import { useEffect, useState } from 'react'

// =============================================================================
// Scene 2: Landing Page
// =============================================================================

export function MockLandingPage({ highlightIndex }: { highlightIndex: number }) {
  const features = [
    { title: '語音故事', desc: 'AI 為孩子量身打造互動故事，搭配多角色語音和精美插圖', icon: BookOpen, color: 'from-blue-500 to-purple-600' },
    { title: '語音互動遊戲', desc: '讓孩子在故事世界中做選擇，體驗沉浸式互動冒險', icon: Gamepad2, color: 'from-green-500 to-teal-600' },
    { title: '適齡萬事通', desc: 'AI 家教用孩子聽得懂的方式回答各種好奇問題', icon: Sparkles, color: 'from-orange-500 to-red-500' },
  ]

  return (
    <div className="flex h-full flex-col items-center justify-center bg-background p-8">
      <div className="mb-12 text-center">
        <h1 className="mb-4 text-4xl font-bold tracking-tight">歡迎來到 StoryPal</h1>
        <p className="text-lg text-muted-foreground">AI 驅動的互動故事與智慧家教，專為孩子設計</p>
      </div>
      <div className="grid max-w-4xl gap-6 md:grid-cols-3">
        {features.map((f, i) => (
          <div
            key={f.title}
            className={`flex flex-col items-center rounded-2xl border bg-card p-8 text-center shadow-sm transition-all duration-500 ${
              i === highlightIndex ? 'ring-4 ring-indigo-400 shadow-lg scale-105' : ''
            }`}
          >
            <div className={`mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br ${f.color} text-white shadow-lg`}>
              <f.icon className="h-8 w-8" />
            </div>
            <h2 className="mb-2 text-xl font-semibold">{f.title}</h2>
            <p className="text-sm text-muted-foreground">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Scene 3: Story Templates
// =============================================================================

const MOCK_TEMPLATES = [
  { name: '海盜冒險記', category: '冒險探索', emoji: '🏴‍☠️', age: '3-6歲', color: 'bg-amber-50 border-amber-200' },
  { name: '魔法學校日記', category: '童話故事', emoji: '🧙‍♂️', age: '4-7歲', color: 'bg-purple-50 border-purple-200' },
  { name: '恐龍探險隊', category: '科學發現', emoji: '🦕', age: '3-6歲', color: 'bg-green-50 border-green-200' },
  { name: '小偵探辦案', category: '冒險探索', emoji: '🔍', age: '5-8歲', color: 'bg-blue-50 border-blue-200' },
  { name: '森林動物派對', category: '寓言故事', emoji: '🌲', age: '2-5歲', color: 'bg-emerald-50 border-emerald-200' },
]

export function MockStoryTemplates({ selectedIndex }: { selectedIndex: number }) {
  return (
    <div className="flex h-full flex-col bg-background">
      <div className="border-b px-6 py-4">
        <h2 className="text-2xl font-bold">選擇故事模板</h2>
        <p className="text-sm text-muted-foreground">為孩子挑選一個精彩的故事冒險</p>
      </div>
      <div className="grid flex-1 grid-cols-3 gap-4 overflow-auto p-6">
        {MOCK_TEMPLATES.map((t, i) => (
          <div
            key={t.name}
            className={`flex flex-col rounded-xl border p-5 transition-all duration-500 ${t.color} ${
              i === selectedIndex ? 'ring-4 ring-indigo-400 shadow-lg scale-105' : 'hover:shadow-md'
            }`}
          >
            <div className="mb-3 text-4xl">{t.emoji}</div>
            <h3 className="mb-1 text-lg font-semibold">{t.name}</h3>
            <p className="text-xs text-muted-foreground">{t.category} &bull; {t.age}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Scene 4: Story Setup & Generation
// =============================================================================

export function MockStorySetup({ phase }: { phase: 'form' | 'generating' }) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (phase !== 'generating') return
    setProgress(0)
    const interval = setInterval(() => {
      setProgress((p) => Math.min(p + 2, 85))
    }, 200)
    return () => clearInterval(interval)
  }, [phase])

  if (phase === 'generating') {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-background p-12">
        <div className="mb-8 text-center">
          <Sparkles className="mx-auto mb-4 h-12 w-12 animate-pulse text-indigo-500" />
          <h2 className="mb-2 text-2xl font-bold">正在生成故事...</h2>
          <p className="text-muted-foreground">AI 正在為小明創作海盜冒險故事</p>
        </div>
        <div className="w-full max-w-md space-y-4">
          <ProgressItem label="故事生成" progress={progress} />
          <ProgressItem label="語音合成" progress={Math.max(0, progress - 30)} />
          <ProgressItem label="場景插圖" progress={Math.max(0, progress - 50)} />
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col bg-background">
      <div className="border-b px-6 py-4">
        <h2 className="text-2xl font-bold">故事設定</h2>
      </div>
      <div className="flex flex-1 gap-8 p-6">
        <div className="flex-1 space-y-5">
          <MockFormField label="孩子名字" value="小明" />
          <MockFormField label="年齡" value="5 歲" />
          <MockFormField label="最喜歡的角色" value="海盜船長" />
          <MockFormField label="學習目標" value="勇氣與冒險精神" />
          <div>
            <div className="mb-1.5 text-sm font-medium">語音模式</div>
            <div className="flex gap-2">
              <span className="rounded-lg bg-indigo-100 px-3 py-1.5 text-sm font-medium text-indigo-700">多角色配音</span>
              <span className="rounded-lg bg-gray-100 px-3 py-1.5 text-sm text-gray-500">單一旁白</span>
            </div>
          </div>
        </div>
        <div className="flex w-48 flex-col items-center justify-center rounded-xl bg-muted/30 p-4">
          <div className="mb-2 text-5xl">🏴‍☠️</div>
          <div className="text-center text-sm font-medium">海盜冒險記</div>
          <div className="text-center text-xs text-muted-foreground">已選模板</div>
        </div>
      </div>
    </div>
  )
}

function MockFormField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="mb-1.5 text-sm font-medium">{label}</div>
      <div className="rounded-lg border bg-muted/30 px-3 py-2 text-sm">{value}</div>
    </div>
  )
}

function ProgressItem({ label, progress }: { label: string; progress: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span>{label}</span>
        <span className="text-muted-foreground">{Math.round(progress)}%</span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  )
}

// =============================================================================
// Scene 5: Story Playing
// =============================================================================

const MOCK_STORY_TURNS = [
  { character: '旁白', text: '在遙遠的加勒比海上，有一座神秘的寶藏島...' },
  { character: '船長鷹眼', text: '小明！快看那邊，我看到寶藏島了！' },
  { character: '小明', text: '真的嗎？我們快去探險吧！' },
  { character: '旁白', text: '小明和鷹眼船長揚起風帆，朝著寶藏島全速前進...' },
]

export function MockStoryPlaying({ showBook }: { showBook: boolean }) {
  const [currentTurn, setCurrentTurn] = useState(0)
  const [isPlaying, setIsPlaying] = useState(true)

  useEffect(() => {
    if (!isPlaying) return
    const interval = setInterval(() => {
      setCurrentTurn((p) => (p + 1) % MOCK_STORY_TURNS.length)
    }, 3000)
    return () => clearInterval(interval)
  }, [isPlaying])

  if (showBook) {
    return (
      <div className="flex h-full bg-amber-50">
        <div className="flex flex-1 items-center justify-center border-r border-amber-200 p-8">
          <div className="flex h-80 w-full items-center justify-center rounded-xl bg-gradient-to-br from-blue-200 to-cyan-100 shadow-inner">
            <div className="text-center">
              <div className="text-6xl">🏴‍☠️🏝️</div>
              <div className="mt-4 text-sm text-gray-500">場景插圖：寶藏島</div>
            </div>
          </div>
        </div>
        <div className="flex flex-1 flex-col justify-center p-8">
          <div className="mb-4 text-2xl font-bold text-amber-900">第一章：出發！</div>
          <div className="space-y-3 text-lg leading-relaxed text-amber-800">
            {MOCK_STORY_TURNS.map((t, i) => (
              <p key={i} className={t.character === '旁白' ? 'italic' : ''}>
                {t.character !== '旁白' && <span className="font-semibold">{t.character}：</span>}
                {t.text}
              </p>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const turn = MOCK_STORY_TURNS[currentTurn]

  return (
    <div className="flex h-full flex-col bg-background">
      {/* Story visual area */}
      <div className="flex flex-1 gap-4 p-4">
        {/* Scene image */}
        <div className="flex flex-1 items-center justify-center rounded-xl bg-gradient-to-br from-blue-200 to-cyan-100">
          <div className="text-center">
            <div className="text-8xl">🏴‍☠️🏝️</div>
            <div className="mt-4 text-sm text-gray-500">場景：加勒比海</div>
          </div>
        </div>
        {/* Character panel */}
        <div className="flex w-48 flex-col items-center justify-center rounded-xl bg-muted/30 p-4">
          <div className="mb-2 text-5xl">{turn.character === '旁白' ? '📖' : turn.character === '船長鷹眼' ? '🏴‍☠️' : '👦'}</div>
          <div className="text-sm font-semibold">{turn.character}</div>
          <div className="mt-2 flex items-center gap-1 text-xs text-green-500">
            <Volume2 className="h-3 w-3" />
            正在說話
          </div>
        </div>
      </div>

      {/* Transcript */}
      <div className="border-t bg-muted/20 p-4">
        <div className="mx-auto max-w-2xl text-center text-lg">
          {turn.character !== '旁白' && <span className="font-bold">{turn.character}：</span>}
          {turn.text}
        </div>
      </div>

      {/* Playback controls */}
      <div className="flex items-center justify-center gap-4 border-t bg-background px-6 py-3">
        <button className="rounded-full p-2 hover:bg-muted" onClick={() => setIsPlaying(!isPlaying)}>
          {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
        </button>
        <SkipForward className="h-5 w-5 text-muted-foreground" />
        <div className="mx-4 h-1.5 flex-1 rounded-full bg-muted">
          <div className="h-full w-1/3 rounded-full bg-indigo-500" />
        </div>
        <span className="text-xs text-muted-foreground">1:23 / 4:56</span>
        <BookOpen className="h-5 w-5 text-muted-foreground" />
      </div>
    </div>
  )
}

// =============================================================================
// Scene 6: Tutor Intro
// =============================================================================

export function MockTutorIntro({ highlightElement }: { highlightElement: 'age' | 'voice' | 'game' | null }) {
  return (
    <div className="flex h-full flex-col bg-background">
      <div className="border-b px-6 py-4">
        <h2 className="text-2xl font-bold">適齡萬事通</h2>
        <p className="text-sm text-muted-foreground">AI 家教即時語音互動</p>
      </div>
      <div className="flex flex-1 gap-6 p-6">
        {/* Config panel */}
        <div className="w-72 space-y-5 rounded-xl border bg-card p-5">
          <div className={`rounded-lg p-3 transition-all duration-500 ${highlightElement === 'age' ? 'ring-2 ring-indigo-400 bg-indigo-50' : ''}`}>
            <div className="mb-1.5 text-sm font-medium">孩子年齡</div>
            <div className="flex gap-2">
              {[3, 4, 5, 6].map((age) => (
                <span key={age} className={`rounded-lg px-3 py-1.5 text-sm ${age === 4 ? 'bg-indigo-100 font-medium text-indigo-700' : 'bg-muted text-muted-foreground'}`}>
                  {age}歲
                </span>
              ))}
            </div>
          </div>
          <div className={`rounded-lg p-3 transition-all duration-500 ${highlightElement === 'voice' ? 'ring-2 ring-indigo-400 bg-indigo-50' : ''}`}>
            <div className="mb-1.5 text-sm font-medium">語音選擇</div>
            <div className="rounded-lg border bg-muted/30 px-3 py-2 text-sm">Kore (溫柔女聲)</div>
          </div>
          <div className={`rounded-lg p-3 transition-all duration-500 ${highlightElement === 'game' ? 'ring-2 ring-indigo-400 bg-indigo-50' : ''}`}>
            <div className="mb-1.5 text-sm font-medium">互動模式</div>
            <div className="flex gap-2">
              <span className="rounded-lg bg-indigo-100 px-3 py-1.5 text-sm font-medium text-indigo-700">自由問答</span>
              <span className="rounded-lg bg-muted px-3 py-1.5 text-sm text-muted-foreground">詞語接龍</span>
            </div>
          </div>
          <button className="w-full rounded-lg bg-indigo-600 py-2.5 text-sm font-medium text-white">
            開始對話
          </button>
        </div>

        {/* Main area placeholder */}
        <div className="flex flex-1 items-center justify-center rounded-xl border-2 border-dashed border-muted">
          <div className="text-center text-muted-foreground">
            <Sparkles className="mx-auto mb-3 h-12 w-12" />
            <p className="text-lg font-medium">準備好了嗎？</p>
            <p className="text-sm">點擊「開始對話」和 AI 家教聊天</p>
          </div>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Scene 7: Tutor Live Demo
// =============================================================================

const MOCK_TUTOR_TRANSCRIPT = [
  { role: 'ai' as const, text: '你好小朋友！我是你的 AI 家教，你可以問我任何問題喔！' },
  { role: 'user' as const, text: '為什麼天空是藍色的？' },
  { role: 'ai' as const, text: '好問題！想像太陽光就像一道彩虹。當陽光穿過天空時，藍色的光最容易被空氣中的小小粒子彈來彈去，所以我們看到的天空就是藍藍的！' },
  { role: 'user' as const, text: '那晚上呢？' },
  { role: 'ai' as const, text: '到了晚上，太陽跑到地球的另一邊去了，沒有陽光照過來，所以天空就變暗了。這時候我們就能看到月亮和星星了！' },
]

export function MockTutorLive({ visibleCount }: { visibleCount: number }) {
  return (
    <div className="flex h-full flex-col bg-background">
      <div className="flex items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-2 w-2 rounded-full bg-green-500" />
          <span className="text-sm font-medium">對話中</span>
          <span className="text-xs text-muted-foreground">02:34</span>
        </div>
        <div className="flex items-center gap-2">
          <Mic className="h-4 w-4 text-green-500" />
          <span className="text-xs text-muted-foreground">收音中</span>
          <Download className="ml-4 h-4 w-4 text-muted-foreground" />
        </div>
      </div>

      {/* Transcript area */}
      <div className="flex-1 space-y-4 overflow-auto p-6">
        {MOCK_TUTOR_TRANSCRIPT.slice(0, visibleCount).map((entry, i) => (
          <div key={i} className={`flex ${entry.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-md rounded-2xl px-4 py-3 ${
                entry.role === 'user'
                  ? 'bg-indigo-600 text-white'
                  : 'bg-muted'
              }`}
            >
              <div className="mb-1 text-xs opacity-60">{entry.role === 'user' ? '小朋友' : 'AI 家教'}</div>
              <div className="text-sm leading-relaxed">{entry.text}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Parent guidance */}
      <div className="border-t bg-amber-50 px-6 py-3">
        <div className="flex items-center gap-2 text-sm text-amber-700">
          <MessageCircle className="h-4 w-4" />
          <span className="font-medium">家長引導：</span>
          <span className="flex-1 text-amber-600">請用更簡單的比喻來解釋</span>
          <ChevronRight className="h-4 w-4" />
        </div>
      </div>

      {/* Quick questions */}
      <div className="flex gap-2 overflow-x-auto border-t px-6 py-3">
        {['為什麼會下雨？', '星星是什麼？', '動物會做夢嗎？'].map((q) => (
          <span key={q} className="flex-shrink-0 rounded-full border bg-card px-3 py-1.5 text-xs">
            {q}
          </span>
        ))}
      </div>
    </div>
  )
}
