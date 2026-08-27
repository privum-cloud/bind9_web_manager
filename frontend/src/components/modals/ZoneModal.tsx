import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { X } from 'lucide-react'
import { zonesAPI } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface ZoneModalProps {
  onClose: () => void
}

export function ZoneModal({ onClose }: ZoneModalProps) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  const [formData, setFormData] = useState({
    name: '',
    type: 'master' as 'master' | 'slave' | 'forward',
    primary_ns: 'ns1.',
    admin_email: 'admin.',
    ttl: 86400,
    refresh: 86400,
    retry: 7200,
    expire: 3600000,
    minimum: 86400,
    master_ip: '',
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) => zonesAPI.create(data),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['zones'] })
      onClose()
      // Navigate to the new zone
      if (res.data?.zone?.name) {
        navigate(`/zones/${res.data.zone.name}`)
      }
    },
    onError: (err: any) => {
      setError(err.response?.data?.error || 'Error creating zone')
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    // Auto-complete NS and admin email with zone name
    const submitData = {
      ...formData,
      primary_ns: formData.primary_ns.endsWith('.')
        ? `${formData.primary_ns}${formData.name}.`
        : formData.primary_ns,
      admin_email: formData.admin_email.endsWith('.')
        ? `${formData.admin_email}${formData.name}.`
        : formData.admin_email,
    }

    createMutation.mutate(submitData)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto py-8">
      <Card className="w-full max-w-2xl mx-4">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>New DNS Zone</CardTitle>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Basic Info */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-muted-foreground">
                Basic Information
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Zone Name *
                  </label>
                  <Input
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    placeholder="example.com"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">
                    Type *
                  </label>
                  <select
                    value={formData.type}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        type: e.target.value as 'master' | 'slave' | 'forward',
                      })
                    }
                    className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm"
                  >
                    <option value="master">Master (Primary)</option>
                    <option value="slave">Slave (Secondary)</option>
                    <option value="forward">Forward</option>
                  </select>
                </div>
              </div>

              {formData.type === 'slave' && (
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Master IP *
                  </label>
                  <Input
                    value={formData.master_ip}
                    onChange={(e) =>
                      setFormData({ ...formData, master_ip: e.target.value })
                    }
                    placeholder="192.168.1.1"
                    required={formData.type === 'slave'}
                  />
                </div>
              )}
            </div>

            {/* SOA Info */}
            {formData.type === 'master' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground">
                  SOA Record
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Primary Nameserver *
                    </label>
                    <Input
                      value={formData.primary_ns}
                      onChange={(e) =>
                        setFormData({ ...formData, primary_ns: e.target.value })
                      }
                      placeholder="ns1.example.com."
                      required
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Use ns1. to auto-complete with the zone name
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Administrator Email *
                    </label>
                    <Input
                      value={formData.admin_email}
                      onChange={(e) =>
                        setFormData({ ...formData, admin_email: e.target.value })
                      }
                      placeholder="admin.example.com."
                      required
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Use admin. to auto-complete with the zone name
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Timing Values */}
            {formData.type === 'master' && (
              <div className="space-y-4">
                <h3 className="text-sm font-medium text-muted-foreground">
                  Time Values (seconds)
                </h3>

                <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">TTL</label>
                    <Input
                      type="number"
                      value={formData.ttl}
                      onChange={(e) =>
                        setFormData({ ...formData, ttl: parseInt(e.target.value) })
                      }
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Refresh
                    </label>
                    <Input
                      type="number"
                      value={formData.refresh}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          refresh: parseInt(e.target.value),
                        })
                      }
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">Retry</label>
                    <Input
                      type="number"
                      value={formData.retry}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          retry: parseInt(e.target.value),
                        })
                      }
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Expire
                    </label>
                    <Input
                      type="number"
                      value={formData.expire}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          expire: parseInt(e.target.value),
                        })
                      }
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Minimum
                    </label>
                    <Input
                      type="number"
                      value={formData.minimum}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          minimum: parseInt(e.target.value),
                        })
                      }
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Error message */}
            {error && (
              <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm">
                {error}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-4 border-t border-border">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Creating...' : 'Create Zone'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
