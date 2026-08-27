import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2, AlertCircle } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { authAPI } from '@/services/api'

export default function SSOCallback() {
  const { isAuthenticated, refreshUser } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const processedRef = useRef(false)

  useEffect(() => {
    // If already authenticated, redirect to home
    if (isAuthenticated) {
      navigate('/')
      return
    }

    // Prevent double processing
    if (processedRef.current) return
    processedRef.current = true

    const processCallback = async () => {
      try {
        // Extract code from URL (can be in hash # or query ?)
        const hash = window.location.hash.substring(1)
        const search = window.location.search.substring(1)
        const params = new URLSearchParams(hash || search)

        const code = params.get('code')
        const sessionState = params.get('session_state')

        console.log('SSO Callback - code:', code ? 'present' : 'missing')
        console.log('SSO Callback - session_state:', sessionState)

        if (!code) {
          throw new Error('No authorization code received from Keycloak')
        }

        // Exchange auth code with backend
        const response = await authAPI.ssoCallback(code)
        const { token, user } = response.data

        // Store auth data
        localStorage.setItem('token', token)
        localStorage.setItem('user', JSON.stringify(user))

        // Refresh auth context and navigate
        await refreshUser()

        // Force page reload to update auth state
        window.location.href = '/'
      } catch (err: unknown) {
        console.error('SSO callback error:', err)
        const errorMessage = err instanceof Error ? err.message : 'SSO authentication failed'
        setError(errorMessage)
        // Redirect to login after a delay
        setTimeout(() => navigate('/login'), 3000)
      }
    }

    processCallback()
  }, [navigate, isAuthenticated, refreshUser])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center max-w-md p-6">
          <AlertCircle className="w-12 h-12 text-destructive mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-foreground mb-2">
            Authentication Failed
          </h2>
          <p className="text-muted-foreground mb-4">{error}</p>
          <p className="text-sm text-muted-foreground">
            Redirecting to login page...
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center">
        <Loader2 className="w-12 h-12 animate-spin text-primary mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-foreground mb-2">
          Completing SSO Login
        </h2>
        <p className="text-muted-foreground">
          Please wait while we authenticate your session...
        </p>
      </div>
    </div>
  )
}
