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
    <header className="flex h-14 items-center gap-3 border-b px-4">
      {showMenu && (
        <Button variant="ghost" size="icon" onClick={onMenuClick} aria-label="Toggle sidebar">
          <Menu className="h-5 w-5" />
        </Button>
      )}
      <h2 className="truncate font-medium">{title}</h2>
    </header>
  )
}
