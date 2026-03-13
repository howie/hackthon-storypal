import { useNavigate } from 'react-router-dom'
import { BookOpen, Sparkles, Gamepad2 } from 'lucide-react'

const features = [
  {
    title: '語音故事',
    description: 'AI 為孩子量身打造互動故事，搭配多角色語音和精美插圖',
    icon: BookOpen,
    href: '/storypal',
    color: 'from-blue-500 to-purple-600',
  },
  {
    title: '語音互動遊戲',
    description: '讓孩子在故事世界中做選擇，體驗沉浸式互動冒險',
    icon: Gamepad2,
    href: '/story-game',
    color: 'from-green-500 to-teal-600',
  },
  {
    title: '適齡萬事通',
    description: 'AI 家教用孩子聽得懂的方式回答各種好奇問題',
    icon: Sparkles,
    href: '/tutor',
    color: 'from-orange-500 to-red-500',
  },
]

export function LandingPage() {
  const navigate = useNavigate()

  return (
    <div className="flex flex-1 flex-col items-center justify-center p-8">
      <div className="mb-12 text-center">
        <h1 className="mb-4 text-4xl font-bold tracking-tight">
          歡迎來到 StoryPal
        </h1>
        <p className="text-lg text-muted-foreground">
          AI 驅動的互動故事與智慧家教，專為孩子設計
        </p>
      </div>

      <div className="grid max-w-4xl gap-6 md:grid-cols-3">
        {features.map((feature) => (
          <button
            key={feature.title}
            onClick={() => navigate(feature.href)}
            className="group flex flex-col items-center rounded-2xl border bg-card p-8 text-center shadow-sm transition-all hover:shadow-lg hover:-translate-y-1"
          >
            <div className={`mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br ${feature.color} text-white shadow-lg`}>
              <feature.icon className="h-8 w-8" />
            </div>
            <h2 className="mb-2 text-xl font-semibold">{feature.title}</h2>
            <p className="text-sm text-muted-foreground">{feature.description}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
