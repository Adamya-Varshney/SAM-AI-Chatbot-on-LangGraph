"use client"

import { useState } from "react"
import { useParams } from "next/navigation"
import { Sidebar } from "@/components/sidebar/sidebar"
import { useMediaQuery } from "@/hooks/use-media-query"

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const isDesktop = useMediaQuery("(min-width: 768px)")
  const params = useParams()
  const threadId = params?.threadId as string | undefined

  return (
    <div className="flex h-dvh overflow-hidden">
      {(isDesktop || sidebarOpen) && (
        <>
          {!isDesktop && sidebarOpen && (
            <div
              className="fixed inset-0 z-40 bg-black/50"
              onClick={() => setSidebarOpen(false)}
            />
          )}
          <div className={!isDesktop ? "fixed inset-y-0 left-0 z-50" : ""}>
            <Sidebar
              open={sidebarOpen}
              onClose={() => setSidebarOpen(false)}
              currentThreadId={threadId}
            />
          </div>
        </>
      )}

      <main className="flex flex-1 flex-col overflow-hidden">
        {children}
      </main>
    </div>
  )
}
