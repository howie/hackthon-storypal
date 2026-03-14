/**
 * LoginPage Component
 * T051: Login page for authentication
 */

import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { LoginButton } from '@/components/auth/LoginButton'
import { LanguageSwitcher } from '@/components/layout/LanguageSwitcher'
import { useLoginRedirect } from '@/hooks/useLoginRedirect'

export function LoginPage() {
  const { isAuthenticated, error, clearError } = useAuthStore()
  const navigate = useNavigate()
  const redirectPath = useLoginRedirect()
  const { t } = useTranslation('auth')

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate(redirectPath, { replace: true })
    }
  }, [isAuthenticated, navigate, redirectPath])

  // Clear error on unmount
  useEffect(() => {
    return () => clearError()
  }, [clearError])

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-background">
      <div className="absolute right-4 top-4">
        <LanguageSwitcher />
      </div>
      <div className="w-full max-w-md space-y-8 rounded-xl border bg-card p-8 shadow-lg">
        {/* Logo / Title */}
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight">{t('login.title')}</h1>
          <p className="mt-2 text-muted-foreground">
            {t('login.subtitle')}
          </p>
        </div>

        {/* Login form */}
        <div className="space-y-6">
          <div className="space-y-2 text-center">
            <h2 className="text-lg font-semibold">{t('login.heading')}</h2>
            <p className="text-sm text-muted-foreground">
              {t('login.description')}
            </p>
          </div>

          {/* Error message */}
          {error && (
            <div className="rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
              <p className="font-medium">{t('login.failed')}</p>
              <p className="mt-1">{error}</p>
            </div>
          )}

          {/* Google login button */}
          <LoginButton className="w-full justify-center" />

        </div>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground">
          {t('login.terms')}
        </p>
      </div>
    </div>
  )
}
