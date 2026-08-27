import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Globe,
  Users,
  FileText,
  Database,
  Settings,
  LogOut,
  LucideIcon,
} from 'lucide-react'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/lib/utils'

type NavPermission = 'view' | 'manage_users' | 'backup' | 'settings' | null

interface NavItem {
  icon: LucideIcon
  label: string
  path: string
  permission: NavPermission
  localAdminOnly?: boolean  // Only show for local admin users
}

const navItems: NavItem[] = [
  { icon: LayoutDashboard, label: 'Dashboard', path: '/', permission: null },
  { icon: Globe, label: 'DNS Zones', path: '/zones', permission: 'view' },
  { icon: Users, label: 'Users', path: '/users', permission: 'manage_users', localAdminOnly: true },
  { icon: FileText, label: 'Audit Log', path: '/audit', permission: 'view' },
  { icon: Database, label: 'Backup', path: '/backup', permission: 'backup' },
  { icon: Settings, label: 'Settings', path: '/settings', permission: 'settings', localAdminOnly: true },
]

export function Sidebar() {
  const location = useLocation()
  const { user, logout, hasPermission } = useAuth()

  // Filter items based on permissions and local admin status
  const isLocalUser = !user?.auth_source || user.auth_source === 'local'

  const filteredNavItems = navItems.filter((item) => {
    if (item.permission === null) return true // Dashboard always visible

    // Check permission first
    const hasRequiredPermission = hasPermission(item.permission as 'view' | 'manage_users' | 'backup' | 'settings')
    if (!hasRequiredPermission) return false

    // If item requires local admin, only show for local users
    if (item.localAdminOnly && !isLocalUser) {
      return false // Hide from SSO users
    }

    return true
  })

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Link to="/" className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center">
            <Globe className="w-6 h-6 text-primary-foreground" />
          </div>
          <div>
            <h1 className="font-semibold text-foreground">DNS Manager</h1>
            <p className="text-xs text-muted-foreground">Web Interface</p>
          </div>
        </Link>
      </div>

      <nav className="sidebar-nav">
        <ul className="space-y-1">
          {filteredNavItems.map((item) => {
            const isActive =
              item.path === '/'
                ? location.pathname === '/'
                : location.pathname.startsWith(item.path)

            return (
              <li key={item.path} className="nav-item">
                <Link
                  to={item.path}
                  className={cn('nav-link', isActive && 'active')}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      <div className="p-4 border-t border-border">
        <Link
          to="/profile"
          className="flex items-center gap-3 mb-3 p-2 -mx-2 rounded-lg hover:bg-accent transition-colors"
        >
          <div className="w-9 h-9 rounded-full bg-primary flex items-center justify-center text-sm font-medium text-primary-foreground">
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.username}</p>
            <p className="text-xs text-muted-foreground truncate">
              {user?.role}
            </p>
          </div>
        </Link>
        <button
          onClick={logout}
          className="flex items-center gap-2 w-full px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent rounded-lg transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Logout</span>
        </button>
      </div>

      <div className="p-4 border-t border-border">
        <p className="text-xs text-muted-foreground text-center">
          PRIVUM DNS Manager v2.0.0
        </p>
      </div>
    </aside>
  )
}
