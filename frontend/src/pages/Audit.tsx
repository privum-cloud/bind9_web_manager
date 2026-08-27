import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Search,
  Plus,
  Edit,
  Trash2,
  RefreshCw,
  User,
  Calendar,
  FileText,
} from 'lucide-react'
import { dashboardAPI } from '@/services/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn, formatDate } from '@/lib/utils'
import type { Activity } from '@/types'

export default function Audit() {
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')

  const { data: activity, isLoading, refetch } = useQuery({
    queryKey: ['audit-activity'],
    queryFn: async () => {
      const res = await dashboardAPI.getActivity()
      return res.data.activity as Activity[]
    },
  })

  const filteredActivity = activity?.filter((item) => {
    const matchesSearch =
      item.action.toLowerCase().includes(search.toLowerCase()) ||
      item.user.toLowerCase().includes(search.toLowerCase()) ||
      item.target.toLowerCase().includes(search.toLowerCase())
    const matchesType = !typeFilter || item.type === typeFilter
    return matchesSearch && matchesType
  })

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'create':
        return <Plus className="w-4 h-4" />
      case 'update':
        return <Edit className="w-4 h-4" />
      case 'delete':
        return <Trash2 className="w-4 h-4" />
      default:
        return <FileText className="w-4 h-4" />
    }
  }

  const getTypeClass = (type: string) => {
    switch (type) {
      case 'create':
        return 'bg-green-500/20 text-green-500'
      case 'update':
        return 'bg-blue-500/20 text-blue-500'
      case 'delete':
        return 'bg-red-500/20 text-red-500'
      default:
        return 'bg-gray-500/20 text-gray-500'
    }
  }

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'create':
        return 'Creation'
      case 'update':
        return 'Update'
      case 'delete':
        return 'Deletion'
      default:
        return type
    }
  }

  // Stats
  const stats = {
    total: activity?.length || 0,
    creates: activity?.filter((a) => a.type === 'create').length || 0,
    updates: activity?.filter((a) => a.type === 'update').length || 0,
    deletes: activity?.filter((a) => a.type === 'delete').length || 0,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Audit</h1>
          <p className="text-muted-foreground">
            System activity history
          </p>
        </div>
        <Button variant="outline" onClick={() => refetch()}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
              <FileText className="w-5 h-5 text-primary" />
            </div>
            <div>
              <p className="text-xl font-bold">{stats.total}</p>
              <p className="text-xs text-muted-foreground">Total</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
              <Plus className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className="text-xl font-bold">{stats.creates}</p>
              <p className="text-xs text-muted-foreground">Creations</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <Edit className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-xl font-bold">{stats.updates}</p>
              <p className="text-xs text-muted-foreground">Updates</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
              <Trash2 className="w-5 h-5 text-red-500" />
            </div>
            <div>
              <p className="text-xl font-bold">{stats.deletes}</p>
              <p className="text-xs text-muted-foreground">Deletions</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="py-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search by action, user or target..."
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
              <option value="create">Creation</option>
              <option value="update">Update</option>
              <option value="delete">Deletion</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Activity List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Activity History</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="py-8 text-center text-muted-foreground">
              Loading...
            </div>
          ) : filteredActivity?.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              No activity found
            </div>
          ) : (
            <div className="divide-y divide-border">
              {filteredActivity?.map((item) => (
                <div
                  key={item.id}
                  className="flex items-start gap-4 p-4 hover:bg-secondary/30"
                >
                  <div
                    className={cn(
                      'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
                      getTypeClass(item.type)
                    )}
                  >
                    {getTypeIcon(item.type)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className={cn(
                          'px-2 py-0.5 rounded text-xs font-medium',
                          getTypeClass(item.type)
                        )}
                      >
                        {getTypeLabel(item.type)}
                      </span>
                      <span className="text-sm font-medium">{item.action}</span>
                    </div>

                    <p className="text-sm text-muted-foreground mt-1">
                      Target: <code className="bg-secondary px-1 rounded">{item.target}</code>
                    </p>

                    <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {item.user}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(item.timestamp)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
