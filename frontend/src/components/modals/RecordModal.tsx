import { useState, useEffect } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X } from 'lucide-react'
import { zonesAPI } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface DNSRecord {
  name: string
  ttl: number
  type: string
  value: string
  priority?: number
}

interface RecordModalProps {
  zoneName: string
  record?: DNSRecord | null
  onClose: () => void
}

const recordTypes = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'PTR', 'SRV', 'CAA']

export function RecordModal({ zoneName, record, onClose }: RecordModalProps) {
  const queryClient = useQueryClient()
  const isEditing = !!record

  const [formData, setFormData] = useState({
    name: '',
    type: 'A',
    value: '',
    ttl: 3600,
    priority: 10,
  })

  useEffect(() => {
    if (record) {
      setFormData({
        name: record.name,
        type: record.type,
        value: record.value,
        ttl: record.ttl,
        priority: record.priority || 10,
      })
    }
  }, [record])

  const createMutation = useMutation({
    mutationFn: (data: typeof formData) =>
      zonesAPI.createRecord(zoneName, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zone', zoneName] })
      onClose()
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: typeof formData) =>
      zonesAPI.updateRecord(zoneName, record!.name, record!.type, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zone', zoneName] })
      onClose()
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (isEditing) {
      updateMutation.mutate(formData)
    } else {
      createMutation.mutate(formData)
    }
  }

  const showPriority = formData.type === 'MX' || formData.type === 'SRV'

  const getPlaceholder = () => {
    switch (formData.type) {
      case 'A':
        return '192.168.1.1'
      case 'AAAA':
        return '2001:db8::1'
      case 'CNAME':
        return 'www.example.com.'
      case 'MX':
        return 'mail.example.com.'
      case 'TXT':
        return 'v=spf1 include:_spf.google.com ~all'
      case 'NS':
        return 'ns1.example.com.'
      case 'PTR':
        return 'host.example.com.'
      case 'SRV':
        return '0 5 5060 sipserver.example.com.'
      case 'CAA':
        return '0 issue "letsencrypt.org"'
      default:
        return ''
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <Card className="w-full max-w-lg mx-4">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>
            {isEditing ? 'Edit Record' : 'New DNS Record'}
          </CardTitle>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2 sm:col-span-1">
                <label className="block text-sm font-medium mb-1">Name</label>
                <Input
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  placeholder="@, www, mail..."
                  disabled={isEditing}
                  required
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Use @ for root domain
                </p>
              </div>

              <div className="col-span-2 sm:col-span-1">
                <label className="block text-sm font-medium mb-1">Type</label>
                <select
                  value={formData.type}
                  onChange={(e) =>
                    setFormData({ ...formData, type: e.target.value })
                  }
                  disabled={isEditing}
                  className="w-full h-10 px-3 rounded-md border border-input bg-background text-sm"
                >
                  {recordTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Value</label>
              <Input
                value={formData.value}
                onChange={(e) =>
                  setFormData({ ...formData, value: e.target.value })
                }
                placeholder={getPlaceholder()}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  TTL (seconds)
                </label>
                <Input
                  type="number"
                  value={formData.ttl}
                  onChange={(e) =>
                    setFormData({ ...formData, ttl: parseInt(e.target.value) })
                  }
                  min={60}
                  required
                />
              </div>

              {showPriority && (
                <div>
                  <label className="block text-sm font-medium mb-1">
                    Priority
                  </label>
                  <Input
                    type="number"
                    value={formData.priority}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        priority: parseInt(e.target.value),
                      })
                    }
                    min={0}
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t border-border">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {isEditing ? 'Save' : 'Create Record'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
