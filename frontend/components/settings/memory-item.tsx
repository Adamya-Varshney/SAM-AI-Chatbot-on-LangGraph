"use client"

import { Trash2, Brain } from "lucide-react"
import { Button } from "@/components/ui/button"

interface MemoryItemProps {
  id: string
  content: string
  category: string
  createdAt: string
  onDelete: (id: string) => void
}

export function MemoryItem({ id, content, category, createdAt, onDelete }: MemoryItemProps) {
  return (
    <div className="group flex items-start gap-3 rounded-lg border p-4">
      <Brain className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
      <div className="flex-1 space-y-1">
        <p className="text-sm">{content}</p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="rounded bg-muted px-1.5 py-0.5">{category}</span>
          <span>{new Date(createdAt).toLocaleDateString()}</span>
        </div>
      </div>
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7 opacity-0 group-hover:opacity-100"
        onClick={() => onDelete(id)}
        aria-label="Delete memory"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>
    </div>
  )
}
