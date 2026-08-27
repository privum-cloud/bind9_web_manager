import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Don't redirect if this is a 2FA required response or login attempt
    const is2FARequired = error.response?.data?.requires_2fa
    const isLoginEndpoint = error.config?.url?.includes('/auth/login')

    if (error.response?.status === 401 && !is2FARequired && !isLoginEndpoint) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

// Auth API
export const authAPI = {
  login: (username: string, password: string, totp_code?: string) =>
    api.post('/auth/login', { username, password, totp_code }),

  me: () => api.get('/auth/me'),

  refresh: () => api.post('/auth/refresh'),

  changePassword: (current_password: string, new_password: string) =>
    api.post('/auth/change-password', { current_password, new_password }),

  // 2FA endpoints
  setup2FA: () => api.post('/auth/2fa/setup'),
  verify2FA: (code: string) => api.post('/auth/2fa/verify', { code }),
  disable2FA: (password: string) => api.post('/auth/2fa/disable', { password }),
  get2FAStatus: () => api.get('/auth/2fa/status'),
  regenerateBackupCodes: (password: string) => api.post('/auth/2fa/backup-codes', { password }),

  // SSO endpoints
  ssoConfig: () => api.get('/auth/sso/config'),
  ssoCallback: (token: string) => api.post('/auth/sso/callback', {
    token,
    redirect_uri: window.location.origin + '/login/callback'
  }),
}

// Dashboard API
export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats'),
  getServers: () => api.get('/dashboard/servers'),
  getActivity: () => api.get('/dashboard/activity'),
  getRecentZones: () => api.get('/dashboard/recent-zones'),
}

// Zones API
export const zonesAPI = {
  list: () => api.get('/zones'),
  get: (name: string) => api.get(`/zones/${name}`),
  create: (data: any) => api.post('/zones', data),
  update: (name: string, data: any) => api.put(`/zones/${name}`, data),
  delete: (name: string) => api.delete(`/zones/${name}`),
  sync: (name: string) => api.post(`/zones/${name}/sync`),

  // Records
  listRecords: (zoneName: string) => api.get(`/zones/${zoneName}/records`),
  createRecord: (zoneName: string, data: any) =>
    api.post(`/zones/${zoneName}/records`, data),
  updateRecord: (zoneName: string, recordName: string, recordType: string, data: any) =>
    api.put(`/zones/${zoneName}/records/${recordName}/${recordType}`, data),
  deleteRecord: (zoneName: string, recordName: string, recordType: string, value?: string) =>
    api.delete(`/zones/${zoneName}/records/${recordName}/${recordType}`, {
      params: value ? { value } : undefined
    }),
}

// Users API
export const usersAPI = {
  list: () => api.get('/users'),
  get: (id: number) => api.get(`/users/${id}`),
  create: (data: any) => api.post('/users', data),
  update: (id: number, data: any) => api.put(`/users/${id}`, data),
  delete: (id: number) => api.delete(`/users/${id}`),
}

// Backup API
export const backupAPI = {
  getSettings: () => api.get('/backup/settings'),
  updateSettings: (data: any) => api.put('/backup/settings', data),
  list: () => api.get('/backup/list'),
  run: () => api.post('/backup/run'),
  restore: (filename: string) => api.post(`/backup/${filename}/restore`),
  delete: (filename: string) => api.delete(`/backup/${filename}`),
  download: (filename: string) => `${API_URL}/backup/${filename}/download`,
}

// Settings API
export const settingsAPI = {
  get: () => api.get('/settings'),
  updateDNS: (data: any) => api.put('/settings/dns', data),
  updateSecurity: (data: any) => api.put('/settings/security', data),
  updateNotifications: (data: any) => api.put('/settings/notifications', data),
  testEmail: () => api.post('/settings/test-email'),
  reloadBind: () => api.post('/settings/reload-bind'),
  flushCache: () => api.post('/settings/flush-cache'),
}
