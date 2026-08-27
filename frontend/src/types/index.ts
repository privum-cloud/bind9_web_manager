// User types
export interface User {
  id: number
  username: string
  email: string
  role: 'admin' | 'operator' | 'viewer'
  active?: boolean
  last_login?: string
  totp_enabled?: boolean
  must_change_password?: boolean
  created_at?: string
  auth_source?: 'local' | 'keycloak'
  is_local_admin?: boolean
}

export interface AuthResponse {
  token: string
  user: User
}

// SSO types
export interface SSOConfig {
  enabled: boolean
  server_url?: string
  realm?: string
  client_id?: string
  local_admin_enabled?: boolean
}

export interface LoginResult {
  success: boolean
  requires2FA?: boolean
  ssoRequired?: boolean
}

// Zone types
export interface Zone {
  name: string
  type: 'master' | 'slave' | 'forward'
  serial: string
  ttl: number
  refresh: number
  retry: number
  expire: number
  minimum: number
  primary_ns: string
  admin_email: string
  record_count?: number
  records?: DNSRecord[]
  status?: 'active' | 'inactive'
}

export interface DNSRecord {
  name: string
  ttl: number
  type: string
  value: string
  priority?: number
}

export interface CreateZoneData {
  name: string
  type?: 'master' | 'slave' | 'forward'
  primary_ns: string
  admin_email: string
  ttl?: number
  refresh?: number
  retry?: number
  expire?: number
  minimum?: number
  master_ip?: string
}

export interface CreateRecordData {
  name: string
  type: string
  value: string
  ttl?: number
  priority?: number
}

// Dashboard types
export interface DashboardStats {
  zones: number
  records: number
  servers: number
  pending: number
}

export interface Server {
  id: number
  name: string
  ip: string
  role: 'master' | 'slave'
  status: 'online' | 'offline'
}

export interface Activity {
  id: number
  type: 'create' | 'update' | 'delete'
  action: string
  target: string
  user: string
  timestamp: string
}

// Backup types
export interface Backup {
  filename: string
  size: number
  size_formatted: string
  created: string
}

export interface BackupSettings {
  enabled: boolean
  frequency: 'hourly' | 'daily' | 'weekly' | 'monthly'
  time: string
  retention: {
    daily: number
    weekly: number
    monthly: number
  }
  destination: 'local' | 's3' | 'gcs' | 'sftp'
  path: string
}

// Settings types
export interface Settings {
  system: {
    version: string
    dns_master: string
    dns_slave: string
    zones_path: string
    backup_path: string
  }
  dns: {
    default_ttl: number
    default_refresh: number
    default_retry: number
    default_expire: number
    default_minimum: number
  }
  security: {
    session_timeout: number
    require_2fa: boolean
    max_login_attempts: number
    lockout_duration: number
  }
  notifications: {
    email_enabled: boolean
    smtp_server: string
    smtp_port: number
    smtp_security: string
  }
}

// API Response types
export interface ApiResponse<T> {
  data?: T
  error?: string
  success?: boolean
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}
