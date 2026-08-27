import { useState, useCallback } from 'react'

interface Toast {
  id: string
  title?: string
  description?: string
  variant?: 'default' | 'destructive' | 'success'
}

let toastId = 0

export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([])

  const toast = useCallback(
    ({ title, description, variant }: Omit<Toast, 'id'>) => {
      const id = String(++toastId)
      setToasts((prev) => [...prev, { id, title, description, variant }])

      // Auto dismiss after 5 seconds
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
      }, 5000)

      return id
    },
    []
  )

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return { toasts, toast, dismiss }
}

// Global toast function
let globalToast: ReturnType<typeof useToast>['toast'] | null = null

export function setGlobalToast(toastFn: typeof globalToast) {
  globalToast = toastFn
}

export function showToast(props: Omit<Toast, 'id'>) {
  if (globalToast) {
    globalToast(props)
  }
}
