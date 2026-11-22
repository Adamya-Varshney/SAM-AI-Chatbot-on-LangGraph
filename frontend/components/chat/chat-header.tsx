"use client"

import { Menu } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ChatHeaderProps {
  title: string
  onMenuClick: () => void
  showMenu: boolean
}

export function ChatHeader({ title, onMenuClick, showMenu }: ChatHeaderProps) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3 sm:h-14 sm:gap-3 sm:px-4">
      {showMenu && (
        <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0" onClick={onMenuClick} aria-label="Toggle sidebar">
          <Menu className="h-5 w-5" />
        </Button>
      )}
      <h2 className="min-w-0 truncate text-sm font-medium sm:text-base">{title}</h2>
    </header>
  )
}
