import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Sparkles,
  Gamepad2,
  Home,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navigationItems = [
  { name: '首頁', href: '/', icon: Home },
  { name: '語音故事', href: '/storypal', icon: BookOpen },
  { name: '語音互動遊戲', href: '/story-game', icon: Gamepad2, label: '實驗' },
  { name: '適齡萬事通', href: '/tutor', icon: Sparkles },
]

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false)

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
              key={item.name}
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
                <span className="flex items-center gap-2">
                  {item.name}
                  {'label' in item && item.label && (
                    <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] leading-none text-muted-foreground">
                      {item.label}
                    </span>
                  )}
                </span>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
      <div className="border-t p-2">
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="flex w-full items-center justify-center rounded-lg p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
          title={isCollapsed ? '展開側邊欄' : '收合側邊欄'}
        >
          {isCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
        {!isCollapsed && (
          <p className="mt-2 text-center text-xs text-muted-foreground">
            StoryPal v1.0.0
          </p>
        )}
      </div>
    </aside>
  )
}
