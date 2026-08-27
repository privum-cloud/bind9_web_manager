/**
 * Keycloak SSO Service
 * Handles Keycloak initialization and authentication
 */
import Keycloak from 'keycloak-js'

let keycloakInstance: Keycloak | null = null
let keycloakInitialized = false

export interface SSOConfig {
  enabled: boolean
  server_url?: string
  realm?: string
  client_id?: string
  local_admin_enabled?: boolean
}

/**
 * Fetch SSO configuration from backend
 */
export async function fetchSSOConfig(): Promise<SSOConfig> {
  const response = await fetch('/api/auth/sso/config')
  if (!response.ok) {
    return { enabled: false }
  }
  return response.json()
}

/**
 * Initialize Keycloak instance with config
 */
export function initKeycloak(config: SSOConfig, forceNew: boolean = false): Keycloak | null {
  if (!config.enabled || !config.server_url || !config.realm || !config.client_id) {
    return null
  }

  // If instance exists and we don't want to force new, return existing
  if (keycloakInstance && !forceNew) {
    return keycloakInstance
  }

  // Create new instance (reset state)
  keycloakInstance = new Keycloak({
    url: config.server_url,
    realm: config.realm,
    clientId: config.client_id
  })
  keycloakInitialized = false

  return keycloakInstance
}

/**
 * Get the current Keycloak instance
 */
export function getKeycloakInstance(): Keycloak | null {
  return keycloakInstance
}

/**
 * Check if Keycloak is initialized
 */
export function isKeycloakInitialized(): boolean {
  return keycloakInstance !== null
}

/**
 * Initialize Keycloak and check for existing session
 */
export async function initAndCheckSSO(config: SSOConfig): Promise<{ authenticated: boolean; token?: string }> {
  const keycloak = initKeycloak(config)

  if (!keycloak) {
    return { authenticated: false }
  }

  try {
    const authenticated = await keycloak.init({
      onLoad: 'check-sso',
      silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
      checkLoginIframe: false
    })

    if (authenticated && keycloak.token) {
      return { authenticated: true, token: keycloak.token }
    }

    return { authenticated: false }
  } catch (error) {
    console.error('Keycloak init error:', error)
    return { authenticated: false }
  }
}

/**
 * Redirect to Keycloak login page
 */
export async function keycloakLogin(): Promise<void> {
  if (!keycloakInstance) {
    throw new Error('Keycloak not initialized')
  }

  // If already initialized, just call login
  if (keycloakInitialized) {
    await keycloakInstance.login({
      redirectUri: window.location.origin + '/login/callback'
    })
    return
  }

  // Initialize and login
  try {
    keycloakInitialized = true
    await keycloakInstance.init({
      onLoad: 'login-required',
      redirectUri: window.location.origin + '/login/callback',
      checkLoginIframe: false
    })
  } catch (error) {
    // If init fails with "already initialized", just do login
    console.log('Keycloak init failed, trying direct login:', error)
    await keycloakInstance.login({
      redirectUri: window.location.origin + '/login/callback'
    })
  }
}

/**
 * Logout from Keycloak
 */
export function keycloakLogout(redirectUri?: string): void {
  if (keycloakInstance?.authenticated) {
    keycloakInstance.logout({
      redirectUri: redirectUri || window.location.origin + '/login'
    })
  }
}

/**
 * Get current Keycloak access token
 */
export function getKeycloakToken(): string | undefined {
  return keycloakInstance?.token
}

/**
 * Check if user is authenticated via Keycloak
 */
export function isKeycloakAuthenticated(): boolean {
  return keycloakInstance?.authenticated ?? false
}

/**
 * Refresh Keycloak token if needed
 */
export async function refreshKeycloakToken(minValidity: number = 30): Promise<boolean> {
  if (!keycloakInstance) {
    return false
  }

  try {
    const refreshed = await keycloakInstance.updateToken(minValidity)
    return refreshed
  } catch (error) {
    console.error('Failed to refresh Keycloak token:', error)
    return false
  }
}

/**
 * Clear Keycloak instance (for cleanup)
 */
export function clearKeycloakInstance(): void {
  keycloakInstance = null
  keycloakInitialized = false
}
