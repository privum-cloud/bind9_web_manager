import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Server,
  Shield,
  Database,
  RefreshCw,
  Trash2,
  Save,
  CheckCircle,
  ShieldX,
} from 'lucide-react'
import { settingsAPI } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'

interface DNSSettings {
  default_ttl: number
  default_refresh: number
  default_retry: number
  default_expire: number
  default_minimum: number
}

interface SecuritySettings {
  session_timeout: number
  max_login_attempts: number
  lockout_duration: number
}

export default function Settings() {
  const { canSettings } = useAuth()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'dns' | 'security' | 'system'>('dns')
  const [saved, setSaved] = useState(false)
  const [actionMessage, setActionMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  // Verificar permissão
  if (!canSettings) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
        <ShieldX className="w-16 h-16 text-destructive" />
        <h1 className="text-2xl font-bold">Access Denied</h1>
        <p className="text-muted-foreground">
          You don't have permission to access settings.
        </p>
      </div>
    )
  }

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const res = await settingsAPI.get()
      return res.data
    },
  })

  const [dnsSettings, setDnsSettings] = useState<DNSSettings>({
    default_ttl: 3600,
    default_refresh: 86400,
    default_retry: 7200,
    default_expire: 3600000,
    default_minimum: 86400,
  })

  const [securitySettings, setSecuritySettings] = useState<SecuritySettings>({
    session_timeout: 30,
    max_login_attempts: 5,
    lockout_duration: 15,
  })

  // Update local state when settings load
  useEffect(() => {
    if (settings?.dns) {
      setDnsSettings(settings.dns)
    }
    if (settings?.security) {
      setSecuritySettings(settings.security)
    }
  }, [settings])

  const saveDNSMutation = useMutation({
    mutationFn: (data: DNSSettings) => settingsAPI.updateDNS(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
  })

  const saveSecurityMutation = useMutation({
    mutationFn: (data: SecuritySettings) => settingsAPI.updateSecurity(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
  })

  const reloadBindMutation = useMutation({
    mutationFn: () => settingsAPI.reloadBind(),
    onSuccess: () => {
      setActionMessage({ type: 'success', text: 'BIND reloaded successfully!' })
      setTimeout(() => setActionMessage(null), 3000)
    },
    onError: () => {
      setActionMessage({ type: 'error', text: 'Failed to reload BIND' })
      setTimeout(() => setActionMessage(null), 3000)
    },
  })

  const flushCacheMutation = useMutation({
    mutationFn: () => settingsAPI.flushCache(),
    onSuccess: () => {
      setActionMessage({ type: 'success', text: 'DNS cache flushed successfully!' })
      setTimeout(() => setActionMessage(null), 3000)
    },
    onError: () => {
      setActionMessage({ type: 'error', text: 'Failed to flush DNS cache' })
      setTimeout(() => setActionMessage(null), 3000)
    },
  })

  const tabs = [
    { id: 'dns', label: 'DNS', icon: Server },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'system', label: 'System', icon: Database },
  ] as const

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Settings</h1>
          <p className="text-muted-foreground">
            Configure system parameters
          </p>
        </div>
        {saved && (
          <div className="flex items-center gap-2 text-green-500">
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm">Saved successfully!</span>
          </div>
        )}
        {actionMessage && (
          <div className={cn(
            "flex items-center gap-2",
            actionMessage.type === 'success' ? 'text-green-500' : 'text-destructive'
          )}>
            <CheckCircle className="w-4 h-4" />
            <span className="text-sm">{actionMessage.text}</span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-t-lg transition-colors',
              activeTab === tab.id
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-secondary'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center py-8 text-muted-foreground">
          Loading...
        </div>
      ) : (
        <>
          {/* DNS Settings */}
          {activeTab === 'dns' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Default DNS Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Default TTL (seconds)
                    </label>
                    <Input
                      type="number"
                      value={dnsSettings.default_ttl}
                      onChange={(e) =>
                        setDnsSettings({
                          ...dnsSettings,
                          default_ttl: parseInt(e.target.value) || 0,
                        })
                      }
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Time to live for DNS records
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Refresh (seconds)
                    </label>
                    <Input
                      type="number"
                      value={dnsSettings.default_refresh}
                      onChange={(e) =>
                        setDnsSettings({
                          ...dnsSettings,
                          default_refresh: parseInt(e.target.value) || 0,
                        })
                      }
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Slave refresh interval
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Retry (seconds)
                    </label>
                    <Input
                      type="number"
                      value={dnsSettings.default_retry}
                      onChange={(e) =>
                        setDnsSettings({
                          ...dnsSettings,
                          default_retry: parseInt(e.target.value) || 0,
                        })
                      }
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Retry interval after failure
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Expire (seconds)
                    </label>
                    <Input
                      type="number"
                      value={dnsSettings.default_expire}
                      onChange={(e) =>
                        setDnsSettings({
                          ...dnsSettings,
                          default_expire: parseInt(e.target.value) || 0,
                        })
                      }
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Max time without master contact
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Minimum TTL (seconds)
                    </label>
                    <Input
                      type="number"
                      value={dnsSettings.default_minimum}
                      onChange={(e) =>
                        setDnsSettings({
                          ...dnsSettings,
                          default_minimum: parseInt(e.target.value) || 0,
                        })
                      }
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      TTL for negative responses
                    </p>
                  </div>
                </div>

                <div className="flex justify-end pt-4">
                  <Button
                    onClick={() => saveDNSMutation.mutate(dnsSettings)}
                    disabled={saveDNSMutation.isPending}
                  >
                    <Save className="w-4 h-4 mr-2" />
                    Save DNS
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Security Settings */}
          {activeTab === 'security' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Security Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Session Timeout (minutes)
                    </label>
                    <Input
                      type="number"
                      value={securitySettings.session_timeout}
                      onChange={(e) =>
                        setSecuritySettings({
                          ...securitySettings,
                          session_timeout: parseInt(e.target.value) || 0,
                        })
                      }
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Max Login Attempts
                    </label>
                    <Input
                      type="number"
                      value={securitySettings.max_login_attempts}
                      onChange={(e) =>
                        setSecuritySettings({
                          ...securitySettings,
                          max_login_attempts: parseInt(e.target.value) || 0,
                        })
                      }
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Lockout Duration (minutes)
                    </label>
                    <Input
                      type="number"
                      value={securitySettings.lockout_duration}
                      onChange={(e) =>
                        setSecuritySettings({
                          ...securitySettings,
                          lockout_duration: parseInt(e.target.value) || 0,
                        })
                      }
                    />
                  </div>
                </div>

                <div className="flex justify-end pt-4">
                  <Button
                    onClick={() => saveSecurityMutation.mutate(securitySettings)}
                    disabled={saveSecurityMutation.isPending}
                  >
                    <Save className="w-4 h-4 mr-2" />
                    Save Security
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* System Settings */}
          {activeTab === 'system' && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">System Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-muted-foreground">Version</span>
                    <span>{settings?.system?.version || '1.0.0'}</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-muted-foreground">DNS Master</span>
                    <code className="text-sm bg-secondary px-2 py-0.5 rounded">
                      {settings?.system?.dns_master || 'dns-master'}
                    </code>
                  </div>
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-muted-foreground">DNS Slave</span>
                    <code className="text-sm bg-secondary px-2 py-0.5 rounded">
                      {settings?.system?.dns_slave || 'dns-slave'}
                    </code>
                  </div>
                  <div className="flex justify-between py-2 border-b border-border/50">
                    <span className="text-muted-foreground">Zones Directory</span>
                    <code className="text-sm bg-secondary px-2 py-0.5 rounded">
                      {settings?.system?.zones_path || '/etc/bind/zones'}
                    </code>
                  </div>
                  <div className="flex justify-between py-2">
                    <span className="text-muted-foreground">Backup Directory</span>
                    <code className="text-sm bg-secondary px-2 py-0.5 rounded">
                      {settings?.system?.backup_path || '/backup'}
                    </code>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">System Actions</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-4 rounded-lg bg-secondary/30">
                    <div>
                      <h3 className="font-medium">Reload BIND</h3>
                      <p className="text-sm text-muted-foreground">
                        Reload DNS server configuration
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => reloadBindMutation.mutate()}
                      disabled={reloadBindMutation.isPending}
                    >
                      {reloadBindMutation.isPending ? (
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <RefreshCw className="w-4 h-4 mr-2" />
                      )}
                      Reload
                    </Button>
                  </div>

                  <div className="flex items-center justify-between p-4 rounded-lg bg-secondary/30">
                    <div>
                      <h3 className="font-medium">Flush DNS Cache</h3>
                      <p className="text-sm text-muted-foreground">
                        Remove all cached records
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => flushCacheMutation.mutate()}
                      disabled={flushCacheMutation.isPending}
                    >
                      {flushCacheMutation.isPending ? (
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Trash2 className="w-4 h-4 mr-2" />
                      )}
                      Flush Cache
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  )
}
