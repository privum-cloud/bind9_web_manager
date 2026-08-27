import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Globe,
  FileText,
  Server,
  Clock,
  Plus,
  RefreshCw,
  Eye,
  ArrowRight,
} from 'lucide-react'
import { dashboardAPI } from '@/services/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn, formatDate } from '@/lib/utils'
import type { DashboardStats, Server as ServerType, Activity, Zone } from '@/types'

export default function Dashboard() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      const res = await dashboardAPI.getStats()
      return res.data as DashboardStats
    },
  })

  const { data: servers, refetch: refetchServers } = useQuery({
    queryKey: ['dashboard-servers'],
    queryFn: async () => {
      const res = await dashboardAPI.getServers()
      return res.data.servers as ServerType[]
    },
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  })

  const { data: activity } = useQuery({
    queryKey: ['dashboard-activity'],
    queryFn: async () => {
      const res = await dashboardAPI.getActivity()
      return res.data.activity as Activity[]
    },
  })

  const { data: recentZones } = useQuery({
    queryKey: ['dashboard-recent-zones'],
    queryFn: async () => {
      const res = await dashboardAPI.getRecentZones()
      return res.data.zones as Zone[]
    },
  })

  const statCards = [
    {
      label: 'Active Zones',
      value: stats?.zones || 0,
      icon: Globe,
      color: 'primary',
    },
    {
      label: 'DNS Records',
      value: stats?.records || 0,
      icon: FileText,
      color: 'info',
    },
    {
      label: 'DNS Servers',
      value: stats?.servers || 0,
      icon: Server,
      color: 'success',
    },
    {
      label: 'Pending',
      value: stats?.pending || 0,
      icon: Clock,
      color: 'warning',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">DNS system overview</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <div key={stat.label} className="stat-card">
            <div className={cn('stat-icon', stat.color)}>
              <stat.icon className="w-6 h-6" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {statsLoading ? '...' : stat.value}
              </p>
              <p className="text-sm text-muted-foreground">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Server Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-lg">Server Status</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => refetchServers()}>
              <RefreshCw className="w-4 h-4" />
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            {servers?.map((server) => (
              <div
                key={server.id}
                className="flex items-center justify-between p-3 rounded-lg bg-secondary/50"
              >
                <div className="flex items-center gap-3">
                  <Server className="w-5 h-5 text-muted-foreground" />
                  <div>
                    <p className="font-medium">{server.name}</p>
                    <p className="text-xs text-muted-foreground">{server.ip}</p>
                  </div>
                </div>
                <span
                  className={cn(
                    'status-badge',
                    server.status === 'online' ? 'online' : 'offline'
                  )}
                >
                  {server.status}
                </span>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-lg">Recent Activity</CardTitle>
            <Link to="/audit">
              <Button variant="ghost" size="sm">
                View All
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="space-y-3">
            {activity?.slice(0, 5).map((item) => (
              <div key={item.id} className="flex items-start gap-3">
                <div
                  className={cn(
                    'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                    item.type === 'create' && 'bg-green-500/20 text-green-500',
                    item.type === 'update' && 'bg-blue-500/20 text-blue-500',
                    item.type === 'delete' && 'bg-red-500/20 text-red-500'
                  )}
                >
                  {item.type === 'create' && <Plus className="w-4 h-4" />}
                  {item.type === 'update' && <RefreshCw className="w-4 h-4" />}
                  {item.type === 'delete' && <Eye className="w-4 h-4" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm">{item.action}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.user} • {formatDate(item.timestamp)}
                  </p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Recent Zones */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-lg">Recent Zones</CardTitle>
          <Link to="/zones">
            <Button variant="ghost" size="sm">
              View All
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
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
                {recentZones?.map((zone) => (
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
                      <span className="px-2 py-1 rounded text-xs bg-secondary">
                        {zone.type}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      {zone.record_count || 0}
                    </td>
                    <td className="py-3 px-4">
                      <code className="text-xs bg-secondary px-2 py-1 rounded">
                        {zone.serial}
                      </code>
                    </td>
                    <td className="py-3 px-4">
                      <span className={cn('status-badge', zone.status)}>
                        {zone.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <Link to={`/zones/${zone.name}`}>
                        <Button variant="ghost" size="sm">
                          <Eye className="w-4 h-4" />
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
