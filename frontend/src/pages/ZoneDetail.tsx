import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeft,
  Plus,
  RefreshCw,
  Edit,
  Trash2,
  Search,
} from 'lucide-react'
import { zonesAPI } from '@/services/api'
import { useAuth } from '@/hooks/useAuth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn, getRecordTypeBadgeClass } from '@/lib/utils'
import { RecordModal } from '@/components/modals/RecordModal'
import { ConfirmModal } from '@/components/modals/ConfirmModal'
import type { Zone } from '@/types'

interface DNSRecord {
  name: string
  ttl: number
  type: string
  value: string
  priority?: number
}

export default function ZoneDetail() {
  const { zoneName } = useParams<{ zoneName: string }>()
  const queryClient = useQueryClient()
  const { canCreate, canEdit, canDelete } = useAuth()
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [showRecordModal, setShowRecordModal] = useState(false)
  const [editingRecord, setEditingRecord] = useState<DNSRecord | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ name: string; type: string; value: string } | null>(null)

  const { data: zone, isLoading } = useQuery({
    queryKey: ['zone', zoneName],
    queryFn: async () => {
      const res = await zonesAPI.get(zoneName!)
      return res.data as Zone
    },
    enabled: !!zoneName,
  })

  const syncMutation = useMutation({
    mutationFn: () => zonesAPI.sync(zoneName!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['zone', zoneName] })
    },
  })

  const deleteRecordMutation = useMutation({
    mutationFn: ({ name, type, value }: { name: string; type: string; value: string }) =>
      zonesAPI.deleteRecord(zoneName!, name, type, value),
    onSuccess: () => {
      setDeleteConfirm(null)
      queryClient.invalidateQueries({ queryKey: ['zone', zoneName] })
    },
  })

  const filteredRecords = zone?.records?.filter((record) => {
    const matchesSearch = record.name.toLowerCase().includes(search.toLowerCase())
    const matchesType = !typeFilter || record.type === typeFilter
    return matchesSearch && matchesType
  })

  const handleDeleteRecord = (name: string, type: string, value: string) => {
    // Close edit modal if open before showing delete confirmation
    if (showRecordModal) {
      setShowRecordModal(false)
      setEditingRecord(null)
    }
    setDeleteConfirm({ name, type, value })
  }

  const confirmDeleteRecord = () => {
    if (deleteConfirm) {
      deleteRecordMutation.mutate(deleteConfirm)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-6 h-6 animate-spin text-primary" />
      </div>
    )
  }

  if (!zone) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">Zone not found</p>
        <Link to="/zones">
          <Button variant="outline" className="mt-4">
            Back to Zones
          </Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/zones">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="w-5 h-5" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold">{zone.name}</h1>
              <span
                className={cn(
                  'px-2 py-1 rounded text-xs font-medium',
                  zone.type === 'master' && 'bg-primary/20 text-primary',
                  zone.type === 'slave' && 'bg-blue-500/20 text-blue-500'
                )}
              >
                {zone.type}
              </span>
            </div>
            <p className="text-muted-foreground">
              {zone.records?.length || 0} records
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending}
          >
            <RefreshCw
              className={cn('w-4 h-4 mr-2', syncMutation.isPending && 'animate-spin')}
            />
            Sync
          </Button>
          {canCreate && (
            <Button onClick={() => { setEditingRecord(null); setShowRecordModal(true); }}>
              <Plus className="w-4 h-4 mr-2" />
              New Record
            </Button>
          )}
        </div>
      </div>

      {/* Zone Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">SOA Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground">Serial</span>
              <code className="text-sm bg-secondary px-2 py-0.5 rounded">
                {zone.serial}
              </code>
            </div>
            <div className="flex justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground">TTL</span>
              <span>{zone.ttl}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground">Refresh</span>
              <span>{zone.refresh}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground">Retry</span>
              <span>{zone.retry}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-muted-foreground">Expire</span>
              <span>{zone.expire}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Server</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground">Primary NS</span>
              <span>{zone.primary_ns}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-border/50">
              <span className="text-muted-foreground">Admin Email</span>
              <span>{zone.admin_email}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-muted-foreground">Status</span>
              <span className="status-badge active">Active</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Records */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-base">DNS Records</CardTitle>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 w-48"
              />
            </div>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="h-10 px-3 rounded-md border border-input bg-background text-sm"
            >
              <option value="">All</option>
              <option value="A">A</option>
              <option value="AAAA">AAAA</option>
              <option value="CNAME">CNAME</option>
              <option value="MX">MX</option>
              <option value="TXT">TXT</option>
              <option value="NS">NS</option>
            </select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-secondary/30">
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    Name
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    TTL
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    Type
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    Value
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredRecords?.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-muted-foreground">
                      No records found
                    </td>
                  </tr>
                ) : (
                  filteredRecords?.map((record, idx) => (
                    <tr
                      key={`${record.name}-${record.type}-${idx}`}
                      className="border-b border-border/50 hover:bg-secondary/30"
                    >
                      <td className="py-3 px-4">
                        <code className="text-sm">{record.name}</code>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {record.ttl}
                      </td>
                      <td className="py-3 px-4">
                        <span className={getRecordTypeBadgeClass(record.type)}>
                          {record.type}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground max-w-xs truncate">
                        {record.value}
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-end gap-1">
                          {canEdit && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8"
                              onClick={() => { setEditingRecord(record); setShowRecordModal(true); }}
                            >
                              <Edit className="w-4 h-4" />
                            </Button>
                          )}
                          {canDelete && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-destructive hover:text-destructive"
                              onClick={() => handleDeleteRecord(record.name, record.type, record.value)}
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

      {/* Record Modal */}
      {showRecordModal && (
        <RecordModal
          zoneName={zoneName!}
          record={editingRecord}
          onClose={() => { setShowRecordModal(false); setEditingRecord(null); }}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <ConfirmModal
          title="Delete Record"
          message={`Are you sure you want to delete the record "${deleteConfirm.name} ${deleteConfirm.type} ${deleteConfirm.value}"?`}
          confirmText="Delete"
          variant="destructive"
          onConfirm={confirmDeleteRecord}
          onCancel={() => setDeleteConfirm(null)}
          isLoading={deleteRecordMutation.isPending}
        />
      )}
    </div>
  )
}
