"use client"

import { Loader2 } from "lucide-react"

interface ToolIndicatorProps {
  label: string
}

export function ToolIndicator({ label }: ToolIndicatorProps) {
  return (
    <div className="flex items-center gap-2 rounded-md bg-muted px-3 py-2 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span>{label}</span>
    </div>
  )
}
