import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { authAPI } from '@/services/api'
import {
  SSOConfig,
  fetchSSOConfig,
  initKeycloak,
  keycloakLogin,
  keycloakLogout,
  clearKeycloakInstance
} from '@/services/keycloak'
import type { User, LoginResult } from '@/types'

// Permissoes por role
const PERMISSIONS = {
  admin: ['create', 'edit', 'delete', 'view', 'manage_users', 'backup', 'settings'],
  operator: ['create', 'edit', 'view', 'backup'],
  viewer: ['view'],
} as const

type Permission = 'create' | 'edit' | 'delete' | 'view' | 'manage_users' | 'backup' | 'settings'

interface AuthContextType {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  mustChangePassword: boolean
  // SSO state
  ssoConfig: SSOConfig | null
  isSSOEnabled: boolean
  isSSOLoading: boolean
  // Methods
  login: (username: string, password: string, totpCode?: string) => Promise<LoginResult>
  loginWithSSO: () => Promise<void>
  handleSSOCallback: () => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
  clearMustChangePassword: () => void
  // Permissoes
  hasPermission: (permission: Permission) => boolean
  isAdmin: boolean
  isOperator: boolean
  isViewer: boolean
  canCreate: boolean
  canEdit: boolean
  canDelete: boolean
  canManageUsers: boolean
  canBackup: boolean
  canSettings: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [ssoConfig, setSSOConfig] = useState<SSOConfig | null>(null)
  const [isSSOLoading, setIsSSOLoading] = useState(true)
  const navigate = useNavigate()

  // Load SSO config and check for existing auth on mount
  useEffect(() => {
    const initAuth = async () => {
      // First, check for stored local auth
      const storedToken = localStorage.getItem('token')
      const storedUser = localStorage.getItem('user')

      if (storedToken && storedUser) {
        setToken(storedToken)
        setUser(JSON.parse(storedUser))
      }

      // Then, load SSO config
      try {
        const config = await fetchSSOConfig()
        setSSOConfig(config)

        if (config.enabled) {
          // Initialize Keycloak for later use
          initKeycloak(config)
        }
      } catch (error) {
        console.error('Failed to load SSO config:', error)
        setSSOConfig({ enabled: false })
      }

      setIsSSOLoading(false)
      setIsLoading(false)
    }

    initAuth()
  }, [])

  // Handle SSO token exchange with backend
  const handleSSOToken = useCallback(async (keycloakToken: string) => {
    try {
      const response = await authAPI.ssoCallback(keycloakToken)
      const { token: newToken, user: newUser } = response.data

      localStorage.setItem('token', newToken)
      localStorage.setItem('user', JSON.stringify(newUser))

      setToken(newToken)
      setUser(newUser)

      return true
    } catch (error) {
      console.error('SSO callback failed:', error)
      throw error
    }
  }, [])

  // Local login (for admin fallback)
  const login = async (username: string, password: string, totpCode?: string): Promise<LoginResult> => {
    try {
      const response = await authAPI.login(username, password, totpCode)
      const { token: newToken, user: newUser } = response.data

      localStorage.setItem('token', newToken)
      localStorage.setItem('user', JSON.stringify(newUser))

      setToken(newToken)
      setUser(newUser)

      navigate('/')
      return { success: true }
    } catch (err: any) {
      // Check if 2FA is required
      if (err.response?.data?.requires_2fa) {
        return { success: false, requires2FA: true }
      }
      // Check if SSO is required
      if (err.response?.data?.sso_required) {
        return { success: false, ssoRequired: true }
      }
      throw err
    }
  }

  // SSO login - redirects to Keycloak
  const loginWithSSO = async () => {
    if (!ssoConfig?.enabled) {
      throw new Error('SSO is not enabled')
    }

    // Initialize Keycloak if needed
    initKeycloak(ssoConfig)

    await keycloakLogin()
  }

  // Handle SSO callback after redirect from Keycloak
  const handleSSOCallback = useCallback(async () => {
    // Wait for SSO config to load if not ready
    if (isSSOLoading) {
      // Config still loading, wait a bit
      await new Promise(resolve => setTimeout(resolve, 500))
    }

    // Get current config (may have been updated)
    let config = ssoConfig
    if (!config?.enabled) {
      // Try to fetch config directly
      try {
        config = await fetchSSOConfig()
      } catch (e) {
        throw new Error('Failed to load SSO configuration')
      }
    }

    if (!config?.enabled) {
      throw new Error('SSO is not enabled')
    }

    // Always create new Keycloak instance on callback (page was reloaded)
    const keycloak = initKeycloak(config, true)

    if (!keycloak) {
      throw new Error('Failed to initialize Keycloak')
    }

    try {
      // Initialize and check if user is authenticated from the redirect
      const authenticated = await keycloak.init({
        onLoad: 'check-sso',
        checkLoginIframe: false
      })

      if (authenticated && keycloak.token) {
        await handleSSOToken(keycloak.token)
        navigate('/')
        return
      } else {
        throw new Error('SSO authentication failed - no token received')
      }
    } catch (error) {
      console.error('SSO callback error:', error)
      throw error
    }
  }, [ssoConfig, isSSOLoading, handleSSOToken, navigate])

  const refreshUser = async () => {
    try {
      const response = await authAPI.me()
      setUser(response.data)
      localStorage.setItem('user', JSON.stringify(response.data))
    } catch (err) {
      console.error('Failed to refresh user:', err)
    }
  }

  const logout = () => {
    // Clear local auth
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)

    // If user logged in via SSO, also logout from Keycloak
    if (user?.auth_source === 'keycloak') {
      clearKeycloakInstance()
      keycloakLogout(window.location.origin + '/login')
    } else {
      navigate('/login')
    }
  }

  // Funcoes de permissao
  const userRole = (user?.role || 'viewer') as keyof typeof PERMISSIONS

  const hasPermission = (permission: Permission): boolean => {
    if (!user) return false
    const rolePermissions = PERMISSIONS[userRole] || []
    return (rolePermissions as readonly string[]).includes(permission)
  }

  const isAdmin = userRole === 'admin'
  const isOperator = userRole === 'operator'
  const isViewer = userRole === 'viewer'

  const canCreate = hasPermission('create')
  const canEdit = hasPermission('edit')
  const canDelete = hasPermission('delete')
  const canManageUsers = hasPermission('manage_users')
  const canBackup = hasPermission('backup')
  const canSettings = hasPermission('settings')

  const mustChangePassword = user?.must_change_password || false

  const clearMustChangePassword = () => {
    if (user) {
      const updatedUser = { ...user, must_change_password: false }
      setUser(updatedUser)
      localStorage.setItem('user', JSON.stringify(updatedUser))
    }
  }

  const isSSOEnabled = ssoConfig?.enabled ?? false

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isLoading,
        mustChangePassword,
        // SSO state
        ssoConfig,
        isSSOEnabled,
        isSSOLoading,
        // Methods
        login,
        loginWithSSO,
        handleSSOCallback,
        logout,
        refreshUser,
        clearMustChangePassword,
        // Permissoes
        hasPermission,
        isAdmin,
        isOperator,
        isViewer,
        canCreate,
        canEdit,
        canDelete,
        canManageUsers,
        canBackup,
        canSettings,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
