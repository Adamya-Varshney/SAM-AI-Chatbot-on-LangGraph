"use client"

import { useRouter } from "next/navigation"
import { Plus, Settings, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ThreadList } from "@/components/sidebar/thread-list"
import { useAuth } from "@/hooks/use-auth"
import { cn } from "@/lib/utils"

interface SidebarProps {
  open: boolean
  onClose?: () => void
  currentThreadId?: string
}

export function Sidebar({ open, onClose, currentThreadId }: SidebarProps) {
  const router = useRouter()
  const { user, signOut } = useAuth()

  const handleNewChat = () => {
    const id = crypto.randomUUID()
    router.push(`/${id}`)
    onClose?.()
  }

  return (
    <aside
      className={cn(
        "flex h-full w-[280px] flex-col border-r bg-card transition-transform duration-200",
        !open && "-translate-x-full md:translate-x-0",
      )}
    >
      <div className="flex items-center justify-between p-4">
        <h1 className="text-lg font-semibold">SAM AI</h1>
        <Button variant="ghost" size="icon" onClick={handleNewChat} aria-label="New chat">
          <Plus className="h-5 w-5" />
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto">
        <ThreadList currentThreadId={currentThreadId} onSelect={onClose} />
      </div>

      <div className="border-t p-4 space-y-2">
        <Button
          variant="ghost"
          className="w-full justify-start gap-2"
          onClick={() => { router.push("/settings"); onClose?.() }}
        >
          <Settings className="h-4 w-4" />
          Settings
        </Button>
        <div className="flex items-center justify-between">
          <span className="truncate text-sm text-muted-foreground">{user?.email}</span>
          <Button variant="ghost" size="icon" onClick={signOut} aria-label="Sign out">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </aside>
  )
}
