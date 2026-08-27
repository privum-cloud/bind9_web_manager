import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Download,
  Trash2,
  RefreshCw,
  Clock,
  HardDrive,
  Calendar,
  Play,
  RotateCcw,
  ShieldX,
} from 'lucide-react'
import { backupAPI } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ConfirmModal } from '@/components/modals/ConfirmModal'
import { cn, formatDate } from '@/lib/utils'
import { useAuth } from '@/hooks/useAuth'
import type { Backup as BackupType } from '@/types'

export default function Backup() {
  const { canBackup } = useAuth()
  const queryClient = useQueryClient()
  const [restoring, setRestoring] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [restoreConfirm, setRestoreConfirm] = useState<BackupType | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<BackupType | null>(null)

  // Check permission
  if (!canBackup) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] space-y-4">
        <ShieldX className="w-16 h-16 text-destructive" />
        <h1 className="text-2xl font-bold">Access Denied</h1>
        <p className="text-muted-foreground">
          You don't have permission to manage backups.
        </p>
      </div>
    )
  }

  const { data: backups, isLoading } = useQuery({
    queryKey: ['backups'],
    queryFn: async () => {
      const res = await backupAPI.list()
      return res.data.backups as BackupType[]
    },
  })

  const runBackupMutation = useMutation({
    mutationFn: () => backupAPI.run(),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['backups'] })
      setError('')
      setSuccess(res.data?.message || 'Backup created successfully!')
      setTimeout(() => setSuccess(''), 5000)
    },
    onError: (err: any) => {
      setSuccess('')
      setError(err.response?.data?.error || 'Error running backup')
    },
  })

  const restoreMutation = useMutation({
    mutationFn: (filename: string) => backupAPI.restore(filename),
    onSuccess: () => {
      setRestoring(null)
      setRestoreConfirm(null)
      queryClient.invalidateQueries({ queryKey: ['backups'] })
      setError('')
      setSuccess('Backup restored successfully!')
      setTimeout(() => setSuccess(''), 5000)
    },
    onError: (err: any) => {
      setRestoring(null)
      setRestoreConfirm(null)
      setError(err.response?.data?.error || 'Error restoring backup')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (filename: string) => backupAPI.delete(filename),
    onSuccess: () => {
      setDeleteConfirm(null)
      queryClient.invalidateQueries({ queryKey: ['backups'] })
      setError('')
      setSuccess('Backup deleted successfully')
      setTimeout(() => setSuccess(''), 3000)
    },
    onError: (err: any) => {
      setDeleteConfirm(null)
      setError(err.response?.data?.error || 'Error deleting backup')
    },
  })

  const handleRestore = (backup: BackupType) => {
    setRestoreConfirm(backup)
  }

  const confirmRestore = () => {
    if (restoreConfirm) {
      setRestoring(restoreConfirm.filename)
      restoreMutation.mutate(restoreConfirm.filename)
    }
  }

  const handleDelete = (backup: BackupType) => {
    setDeleteConfirm(backup)
  }

  const confirmDelete = () => {
    if (deleteConfirm) {
      deleteMutation.mutate(deleteConfirm.filename)
    }
  }

  const totalSize = backups?.reduce((acc, b) => acc + b.size, 0) || 0
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Backups</h1>
          <p className="text-muted-foreground">
            Manage DNS zone backups
          </p>
        </div>
        <Button
          onClick={() => runBackupMutation.mutate()}
          disabled={runBackupMutation.isPending}
        >
          {runBackupMutation.isPending ? (
            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Play className="w-4 h-4 mr-2" />
          )}
          Run Backup
        </Button>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-3 rounded-lg bg-destructive/10 text-destructive text-sm flex items-center justify-between">
          {error}
          <button onClick={() => setError('')} className="text-destructive hover:opacity-80">×</button>
        </div>
      )}
      {success && (
        <div className="p-3 rounded-lg bg-green-500/10 text-green-500 text-sm flex items-center justify-between">
          {success}
          <button onClick={() => setSuccess('')} className="text-green-500 hover:opacity-80">×</button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-primary/20 flex items-center justify-center">
              <HardDrive className="w-6 h-6 text-primary" />
            </div>
            <div>
              <p className="text-2xl font-bold">{backups?.length || 0}</p>
              <p className="text-sm text-muted-foreground">Total Backups</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <Calendar className="w-6 h-6 text-blue-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {backups?.[0] ? formatDate(backups[0].created) : 'N/A'}
              </p>
              <p className="text-sm text-muted-foreground">Last Backup</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-green-500/20 flex items-center justify-center">
              <Clock className="w-6 h-6 text-green-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{formatSize(totalSize)}</p>
              <p className="text-sm text-muted-foreground">Space Used</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Backup List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Backup List</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border bg-secondary/30">
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    File
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    Date
                  </th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-muted-foreground">
                    Size
                  </th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-muted-foreground">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-muted-foreground">
                      Loading...
                    </td>
                  </tr>
                ) : backups?.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="py-8 text-center text-muted-foreground">
                      No backups found
                    </td>
                  </tr>
                ) : (
                  backups?.map((backup) => (
                    <tr
                      key={backup.filename}
                      className="border-b border-border/50 hover:bg-secondary/30"
                    >
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <HardDrive className="w-4 h-4 text-muted-foreground" />
                          <code className="text-sm">{backup.filename}</code>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {formatDate(backup.created)}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-1 rounded text-xs bg-secondary">
                          {backup.size_formatted || formatSize(backup.size)}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center justify-end gap-1">
                          <a
                            href={backupAPI.download(backup.filename)}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <Download className="w-4 h-4" />
                            </Button>
                          </a>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => handleRestore(backup)}
                            disabled={restoring === backup.filename}
                          >
                            <RotateCcw
                              className={cn(
                                'w-4 h-4',
                                restoring === backup.filename && 'animate-spin'
                              )}
                            />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            onClick={() => handleDelete(backup)}
                            disabled={deleteMutation.isPending}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
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

      {/* Restore Confirmation Modal */}
      {restoreConfirm && (
        <ConfirmModal
          title="Restore Backup"
          message={`Are you sure you want to restore backup "${restoreConfirm.filename}"? This will overwrite current settings.`}
          confirmText="Restore"
          variant="default"
          onConfirm={confirmRestore}
          onCancel={() => setRestoreConfirm(null)}
          isLoading={restoreMutation.isPending}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <ConfirmModal
          title="Delete Backup"
          message={`Are you sure you want to delete backup "${deleteConfirm.filename}"? This action cannot be undone.`}
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
