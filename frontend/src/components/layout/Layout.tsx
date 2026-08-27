import { ReactNode, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/hooks/useAuth'
import { Sidebar } from './Sidebar'
import { ChangePasswordModal } from '@/components/modals/ChangePasswordModal'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const { isAuthenticated, isLoading, mustChangePassword } = useAuth()
  const [showPasswordModal, setShowPasswordModal] = useState(true)

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="main-content p-6">{children}</main>

      {/* Mandatory password change modal */}
      {mustChangePassword && showPasswordModal && (
        <ChangePasswordModal onSuccess={() => setShowPasswordModal(false)} />
      )}
    </div>
  )
}
