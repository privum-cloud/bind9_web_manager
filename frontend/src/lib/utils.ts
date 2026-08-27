import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  const d = new Date(date)
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

export function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function getRecordTypeBadgeClass(type: string): string {
  const baseClass = "px-2 py-1 rounded text-xs font-medium"
  const typeClasses: Record<string, string> = {
    A: "bg-blue-500/20 text-blue-400",
    AAAA: "bg-cyan-500/20 text-cyan-400",
    CNAME: "bg-purple-500/20 text-purple-400",
    MX: "bg-orange-500/20 text-orange-400",
    TXT: "bg-green-500/20 text-green-400",
    NS: "bg-yellow-500/20 text-yellow-400",
    SRV: "bg-pink-500/20 text-pink-400",
    PTR: "bg-indigo-500/20 text-indigo-400",
    SOA: "bg-red-500/20 text-red-400",
  }
  return cn(baseClass, typeClasses[type] || "bg-gray-500/20 text-gray-400")
}
