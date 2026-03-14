import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Sparkles,
  Disc3,
  Home,
  Play,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const { t } = useTranslation()

  const navigationItems = [
    { name: t('nav.home'), href: '/', icon: Home },
    { name: t('nav.voiceStory'), href: '/storypal', icon: BookOpen },
    { name: t('nav.magicDJ'), href: '/magic-dj', icon: Disc3 },
    { name: t('nav.tutor'), href: '/tutor', icon: Sparkles },
    { name: t('nav.demo'), href: '/demo', icon: Play },
  ]

  return (
    <aside
      className={cn(
        'flex shrink-0 flex-col border-r bg-card transition-all duration-300',
        isCollapsed ? 'w-16' : 'w-fit'
      )}
    >
      <div
        className={cn(
          'flex h-12 items-center border-b',
          isCollapsed ? 'justify-center px-2' : 'gap-2 px-3'
        )}
      >
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <BookOpen className="h-3.5 w-3.5" />
        </div>
        {!isCollapsed && (
          <span className="text-sm font-semibold">StoryPal</span>
        )}
      </div>
      <nav className="flex-1 overflow-y-auto p-2">
        <div className="space-y-0.5">
          {navigationItems.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              end={item.href === '/'}
              title={isCollapsed ? item.name : undefined}
              className={({ isActive }) =>
                cn(
                  'flex items-center whitespace-nowrap rounded-md text-sm font-medium transition-colors',
                  isCollapsed ? 'justify-center p-2' : 'gap-2 px-2 py-1.5',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )
              }
            >
              <item.icon className="h-3.5 w-3.5 shrink-0" />
              {!isCollapsed && (
                <span>{item.name}</span>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
      <div className="border-t p-2">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="flex w-full items-center justify-center rounded-lg p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          title={isCollapsed ? t('sidebar.expand') : t('sidebar.collapse')}
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
        {!isCollapsed && (
          <p className="mt-2 text-center text-xs text-muted-foreground">
            {t('sidebar.version')}
          </p>
        )}
      </div>
    </aside>
  )
}
