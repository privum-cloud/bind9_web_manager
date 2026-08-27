import { useToast } from "@/hooks/useToast"
import { X } from "lucide-react"

export function Toaster() {
  const { toasts, dismiss } = useToast()

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`
            flex items-center gap-3 px-4 py-3 rounded-lg shadow-lg min-w-[300px] max-w-[450px]
            animate-in slide-in-from-right-full
            ${toast.variant === 'destructive' ? 'bg-destructive text-destructive-foreground' : ''}
            ${toast.variant === 'success' ? 'bg-green-500 text-white' : ''}
            ${!toast.variant ? 'bg-card border border-border text-foreground' : ''}
          `}
        >
          <div className="flex-1">
            {toast.title && <p className="font-medium">{toast.title}</p>}
            {toast.description && (
              <p className="text-sm opacity-90">{toast.description}</p>
            )}
          </div>
          <button
            onClick={() => dismiss(toast.id)}
            className="opacity-70 hover:opacity-100"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
