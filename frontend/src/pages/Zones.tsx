import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Plus,
  Search,
  RefreshCw,
  Eye,
  Trash2,
} from 'lucide-react'
import { zonesAPI } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { ZoneModal } from '@/components/modals/ZoneModal'
import { ConfirmModal } from '@/components/modals/ConfirmModal'
import { useAuth } from '@/hooks/useAuth'
import type { Zone } from '@/types'

export default function Zones() {
  const { canCreate, canEdit, canDelete } = useAuth()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [showZoneModal, setShowZoneModal] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const { data: zones, isLoading } = useQuery({
    queryKey: ['zones'],
    queryFn: async () => {
      const res = await zonesAPI.list()
      return res.data.zones as Zone[]
    },
  })

  const syncMutation = useMutation({
    mutationFn: (zoneName: string) => zonesAPI.sync(zoneName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zones'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (zoneName: string) => zonesAPI.delete(zoneName),
    onSuccess: () => {
      setDeleteConfirm(null)
      queryClient.invalidateQueries({ queryKey: ['zones'] })
    },
  })

  const filteredZones = zones?.filter((zone) => {
    const matchesSearch = zone.name.toLowerCase().includes(search.toLowerCase())
    const matchesType = !typeFilter || zone.type === typeFilter
    return matchesSearch && matchesType
  })

  const handleDelete = (zoneName: string) => {
    setDeleteConfirm(zoneName)
  }

  const confirmDelete = () => {
    if (deleteConfirm) {
      deleteMutation.mutate(deleteConfirm)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">DNS Zones</h1>
          <p className="text-muted-foreground">
            Manage your DNS zones and records
          </p>
        </div>
{canCreate && (
          <Button onClick={() => setShowZoneModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            New Zone
          </Button>
        )}
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search zones..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="h-10 px-3 rounded-md border border-input bg-background text-sm"
            >
              <option value="">All types</option>
              <option value="master">Master</option>
              <option value="slave">Slave</option>
              <option value="forward">Forward</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Zones Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-secondary/30">
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    Zone
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    Type
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    Records
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    Serial
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    Status
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-muted-foreground">
                      Loading...
                    </td>
                  </tr>
                ) : filteredZones?.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-muted-foreground">
                      No zones found
                    </td>
                  </tr>
                ) : (
                  filteredZones?.map((zone) => (
                    <tr
                      key={zone.name}
                      className="border-b border-border/50 hover:bg-secondary/30"
                    >
                      <td className="py-3 px-4">
                        <Link
                          to={`/zones/${zone.name}`}
                          className="text-primary hover:underline font-medium"
                        >
                          {zone.name}
                        </Link>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={cn(
                            'px-2 py-1 rounded text-xs font-medium',
                            zone.type === 'master' && 'bg-primary/20 text-primary',
                            zone.type === 'slave' && 'bg-blue-500/20 text-blue-500',
                            zone.type === 'forward' && 'bg-yellow-500/20 text-yellow-500'
                          )}
                        >
                          {zone.type}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {zone.record_count || 0}
                      </td>
                      <td className="py-3 px-4">
                        <code className="text-xs bg-secondary px-2 py-1 rounded">
                          {zone.serial || 'N/A'}
                        </code>
                      </td>
                      <td className="py-3 px-4">
                        <span className="status-badge active">active</span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-end gap-1">
                          <Link to={`/zones/${zone.name}`}>
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <Eye className="w-4 h-4" />
                            </Button>
                          </Link>
                          {canEdit && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => syncMutation.mutate(zone.name)}
                              disabled={syncMutation.isPending}
                            >
                              <RefreshCw
                                className={cn(
                                  'w-4 h-4',
                                  syncMutation.isPending && 'animate-spin'
                                )}
                              />
                            </Button>
                          )}
                          {canDelete && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-destructive hover:text-destructive"
                              onClick={() => handleDelete(zone.name)}
                              disabled={deleteMutation.isPending}
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Zone Modal */}
      {showZoneModal && (
        <ZoneModal onClose={() => setShowZoneModal(false)} />
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <ConfirmModal
          title="Delete Zone"
          message={`Are you sure you want to delete zone "${deleteConfirm}"? This action cannot be undone.`}
          confirmText="Delete"
          variant="destructive"
          onConfirm={confirmDelete}
          onCancel={() => setDeleteConfirm(null)}
          isLoading={deleteMutation.isPending}
        />
      )}
    </div>
  )
}
