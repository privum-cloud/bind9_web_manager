import { useState, useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import { Globe, Loader2, Shield, ArrowLeft, KeyRound, User } from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function Login() {
  const {
    login,
    loginWithSSO,
    isAuthenticated,
    isLoading: authLoading,
    ssoConfig,
    isSSOEnabled,
    isSSOLoading
  } = useAuth()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [requires2FA, setRequires2FA] = useState(false)
  const [loginMode, setLoginMode] = useState<'sso' | 'local'>('sso')

  // Set default login mode based on SSO config
  useEffect(() => {
    if (!isSSOLoading) {
      setLoginMode(isSSOEnabled ? 'sso' : 'local')
    }
  }, [isSSOEnabled, isSSOLoading])

  if (authLoading || isSSOLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (isAuthenticated) {
    return <Navigate to="/" replace />
  }

  const handleLocalSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const result = await login(username, password, requires2FA ? totpCode : undefined)

      if (result.requires2FA) {
        setRequires2FA(true)
        setError('')
      } else if (result.ssoRequired) {
        setError('Local login is restricted. Please use SSO.')
        setLoginMode('sso')
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Error logging in')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSSOLogin = async () => {
    setIsLoading(true)
    setError('')
    try {
      await loginWithSSO()
      // Redirect happens automatically
    } catch (err: any) {
      setError('SSO login failed. Please try again.')
      setIsLoading(false)
    }
  }

  const handleBack = () => {
    setRequires2FA(false)
    setTotpCode('')
    setError('')
  }

  // Local login form JSX
  const localLoginForm = (
    <form onSubmit={handleLocalSubmit} className="space-y-4">
      {!requires2FA ? (
        <>
          {isSSOEnabled && (
            <p className="text-sm text-muted-foreground text-center mb-4">
              User Login Restricted
            </p>
          )}
          <div className="space-y-2">
            <label htmlFor="username" className="text-sm font-medium">
              Username
            </label>
            <Input
              id="username"
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="password" className="text-sm font-medium">
              Password
            </label>
            <Input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
        </>
      ) : (
        <>
          <div className="space-y-2">
            <label htmlFor="totp" className="text-sm font-medium">
              Verification Code
            </label>
            <Input
              id="totp"
              type="text"
              placeholder="000000"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 8))}
              required
              autoComplete="one-time-code"
              className="text-center text-2xl tracking-widest font-mono"
              autoFocus
            />
            <p className="text-xs text-muted-foreground text-center">
              Or use a backup code
            </p>
          </div>

          <Button
            type="button"
            variant="ghost"
            className="w-full"
            onClick={handleBack}
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
        </>
      )}

      <Button type="submit" className="w-full" disabled={isLoading}>
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            {requires2FA ? 'Verifying...' : 'Signing in...'}
          </>
        ) : (
          requires2FA ? 'Verify' : 'Sign In'
        )}
      </Button>
    </form>
  )

  // SSO login button JSX
  const ssoLoginButton = (
    <div className="space-y-4">
      <Button
        onClick={handleSSOLogin}
        className="w-full"
        disabled={isLoading}
        size="lg"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            Redirecting to SSO...
          </>
        ) : (
          <>
            <KeyRound className="w-4 h-4 mr-2" />
            Sign in with Keycloak
          </>
        )}
      </Button>
      <p className="text-center text-xs text-muted-foreground">
        You will be redirected to your organization's login page
      </p>
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-background to-secondary">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-4">
            {requires2FA ? (
              <Shield className="w-8 h-8 text-primary" />
            ) : (
              <Globe className="w-8 h-8 text-primary" />
            )}
          </div>
          <CardTitle className="text-2xl">
            {requires2FA ? '2FA Authentication' : 'DNS Web Manager'}
          </CardTitle>
          <CardDescription>
            {requires2FA
              ? 'Enter the code from your authenticator app'
              : 'Sign in to manage your DNS zones'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {error && (
            <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm mb-4">
              {error}
            </div>
          )}

          {!requires2FA && isSSOEnabled && ssoConfig?.local_admin_enabled ? (
            // Dual mode: SSO + Local admin
            <Tabs value={loginMode} onValueChange={(v: string) => setLoginMode(v as 'sso' | 'local')}>
              <TabsList className="grid w-full grid-cols-2 mb-4">
                <TabsTrigger value="sso">
                  <KeyRound className="w-4 h-4 mr-2" />
                  SSO Login
                </TabsTrigger>
                <TabsTrigger value="local">
                  <User className="w-4 h-4 mr-2" />
                  Admin Login
                </TabsTrigger>
              </TabsList>

              <TabsContent value="sso">
                {ssoLoginButton}
              </TabsContent>

              <TabsContent value="local">
                {localLoginForm}
              </TabsContent>
            </Tabs>
          ) : isSSOEnabled ? (
            // SSO only mode
            ssoLoginButton
          ) : (
            // Local only mode (no SSO configured)
            localLoginForm
          )}

          <p className="mt-6 text-center text-xs text-muted-foreground">
            PRIVUM DNS Manager v2.0.0
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
