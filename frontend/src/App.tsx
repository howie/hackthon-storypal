import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { LoginPage } from '@/routes/auth/LoginPage'
import { AuthCallback } from '@/routes/auth/AuthCallback'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { useAuthStore } from '@/stores/authStore'
import { Spinner } from '@/components/shared/Spinner'

// Lazy-loaded route pages
const StoryPage = lazy(() => import('@/routes/storypal/StoryPage').then(m => ({ default: m.StoryPage })))
const StoryGamePage = lazy(() => import('@/routes/story-game/StoryGamePage').then(m => ({ default: m.StoryGamePage })))
const TutorPage = lazy(() => import('@/routes/tutor/TutorPage').then(m => ({ default: m.TutorPage })))
const LandingPage = lazy(() => import('@/routes/LandingPage').then(m => ({ default: m.LandingPage })))
const DemoPage = lazy(() => import('@/routes/demo/DemoPage').then(m => ({ default: m.DemoPage })))

function AppContent() {
  const checkAuth = useAuthStore((state) => state.checkAuth)
  const setToken = useAuthStore((state) => state.setToken)

  // Handle OAuth token from URL and check auth
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    const error = params.get('error')

    if (token) {
      setToken(token)
      window.history.replaceState({}, '', window.location.pathname)
      checkAuth()
    } else if (error) {
      console.error('OAuth error:', error)
      window.history.replaceState({}, '', window.location.pathname)
      checkAuth()
    } else {
      checkAuth()
    }
  }, [setToken, checkAuth])

  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center"><Spinner className="h-8 w-8" /></div>}>
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/demo" element={<DemoPage />} />

      {/* Protected routes */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<LandingPage />} />
        <Route path="storypal" element={<StoryPage />} />
        <Route path="story-game" element={<StoryGamePage />} />
        <Route path="tutor" element={<TutorPage />} />
        <Route path="storypal/tutor" element={<Navigate to="/tutor" replace />} />
      </Route>
    </Routes>
    </Suspense>
  )
}

function App() {
  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <AppContent />
    </BrowserRouter>
  )
}

export default App
