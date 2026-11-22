"use client"

import { useParams } from "next/navigation"
import { Sidebar } from "@/components/sidebar/sidebar"
import { useMediaQuery } from "@/hooks/use-media-query"
import { SidebarProvider, useSidebar } from "@/hooks/use-sidebar"

function ChatLayoutInner({ children }: { children: React.ReactNode }) {
  const { open, close } = useSidebar()
  const isDesktop = useMediaQuery("(min-width: 768px)")
  const params = useParams()
  const threadId = params?.threadId as string | undefined

  return (
    <div className="flex h-dvh overflow-hidden">
      {(isDesktop || open) && (
        <>
          {!isDesktop && open && (
            <div
              className="fixed inset-0 z-40 bg-black/50"
              onClick={close}
            />
          )}
          <div className={!isDesktop ? "fixed inset-y-0 left-0 z-50" : ""}>
            <Sidebar
              open={open}
              onClose={close}
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

export default function ChatLayout({ children }: { children: React.ReactNode }) {
  return (
    <SidebarProvider>
      <ChatLayoutInner>{children}</ChatLayoutInner>
    </SidebarProvider>
  )
}
