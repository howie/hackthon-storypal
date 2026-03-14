import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'

export function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const isZh = i18n.language.startsWith('zh')

  return (
    <div className="flex items-center rounded-lg border bg-muted p-0.5 text-xs font-medium">
      <button
        onClick={() => i18n.changeLanguage('zh-TW')}
        className={cn(
          'rounded-md px-2 py-1 transition-colors',
          isZh
            ? 'bg-background text-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        )}
      >
        中文
      </button>
      <button
        onClick={() => i18n.changeLanguage('en')}
        className={cn(
          'rounded-md px-2 py-1 transition-colors',
          !isZh
            ? 'bg-background text-foreground shadow-sm'
            : 'text-muted-foreground hover:text-foreground'
        )}
      >
        EN
      </button>
    </div>
  )
}
