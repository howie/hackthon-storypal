import { useNavigate } from 'react-router-dom'
import { BookOpen, Sparkles, Gamepad2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export function LandingPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()

  const features = [
    {
      title: t('nav.voiceStory'),
      description: t('landing.voiceStoryDesc'),
      icon: BookOpen,
      href: '/storypal',
      color: 'from-blue-500 to-purple-600',
    },
    {
      title: t('nav.voiceGame'),
      description: t('landing.voiceGameDesc'),
      icon: Gamepad2,
      href: '/story-game',
      color: 'from-green-500 to-teal-600',
    },
    {
      title: t('nav.tutor'),
      description: t('landing.tutorDesc'),
      icon: Sparkles,
      href: '/tutor',
      color: 'from-orange-500 to-red-500',
    },
  ]

  return (
    <div className="flex flex-1 flex-col items-center justify-center p-8">
      <div className="mb-12 text-center">
        <h1 className="mb-4 text-4xl font-bold tracking-tight">
          {t('landing.welcome')}
        </h1>
        <p className="text-lg text-muted-foreground">
          {t('landing.subtitle')}
        </p>
      </div>

      <div className="grid max-w-4xl gap-6 md:grid-cols-3">
        {features.map((feature) => (
          <button
            key={feature.href}
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
