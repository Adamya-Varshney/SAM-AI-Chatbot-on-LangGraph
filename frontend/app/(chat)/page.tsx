"use client"

import { useRouter } from "next/navigation"
import { ChatHeader } from "@/components/chat/chat-header"
import { WelcomeScreen } from "@/components/chat/welcome-screen"
import { InputArea } from "@/components/chat/input-area"
import { useMediaQuery } from "@/hooks/use-media-query"
import { useSidebar } from "@/hooks/use-sidebar"

export default function NewChatPage() {
  const router = useRouter()
  const isDesktop = useMediaQuery("(min-width: 768px)")
  const { toggle: toggleSidebar } = useSidebar()

  const handleSend = (message: string) => {
    const threadId = crypto.randomUUID()
    const params = new URLSearchParams({ prompt: message })
    router.push(`/${threadId}?${params.toString()}`)
  }

  return (
    <>
      <ChatHeader
        title="New Chat"
        onMenuClick={toggleSidebar}
        showMenu={!isDesktop}
      />
      <WelcomeScreen onSuggestionClick={handleSend} />
      <InputArea onSubmit={handleSend} isLoading={false} />
    </>
  )
}
