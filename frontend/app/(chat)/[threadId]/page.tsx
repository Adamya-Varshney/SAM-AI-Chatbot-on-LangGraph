"use client"

import { useParams, useSearchParams } from "next/navigation"
import { useEffect, useRef, useState, useCallback } from "react"
import { ChatHeader } from "@/components/chat/chat-header"
import { MessageList } from "@/components/chat/message-list"
import { InputArea } from "@/components/chat/input-area"
import { useAuth } from "@/hooks/use-auth"
import { useMediaQuery } from "@/hooks/use-media-query"
import { apiFetch } from "@/lib/api"

interface Message {
  role: "user" | "assistant"
  content: string
}

export default function ThreadPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const threadId = params.threadId as string
  const { session } = useAuth()
  const isDesktop = useMediaQuery("(min-width: 768px)")

  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [activeTool, setActiveTool] = useState<string | null>(null)
  const [title, setTitle] = useState("New Chat")
  const initialPromptHandled = useRef(false)

  const loadThread = useCallback(async () => {
    if (!session) return
    try {
      const data = await apiFetch<{ title: string; messages: Message[] }>(
        `/api/threads/${threadId}`,
        session.access_token,
      )
      setTitle(data.title)
      setMessages(data.messages)
    } catch {
      // New thread, no messages yet
    }
  }, [session, threadId])

  const sendMessage = useCallback(async (content: string, file?: File) => {
    if (!session || isStreaming) return

    setMessages((prev) => [...prev, { role: "user", content }])
    setIsStreaming(true)
    setActiveTool(null)

    if (file) {
      const formData = new FormData()
      formData.append("file", file)
      formData.append("thread_id", threadId)
      try {
        await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/documents/upload`, {
          method: "POST",
          headers: { Authorization: `Bearer ${session.access_token}` },
          body: formData,
        })
      } catch {
        // Upload error handled silently for now
      }
    }

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.access_token}`,
        },
        body: JSON.stringify({ thread_id: threadId, message: content }),
      })

      if (!response.ok || !response.body) {
        throw new Error("Stream failed")
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ""
      setMessages((prev) => [...prev, { role: "assistant", content: "" }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split("\n")

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue
          const data = line.slice(6)

          try {
            const event = JSON.parse(data)
            switch (event.type) {
              case "token":
                assistantContent += event.content
                setMessages((prev) => {
                  const updated = [...prev]
                  updated[updated.length - 1] = { role: "assistant", content: assistantContent }
                  return updated
                })
                break
              case "tool_start":
                setActiveTool(`Using ${event.tool}...`)
                break
              case "tool_end":
                setActiveTool(null)
                break
              case "done":
                if (event.title) setTitle(event.title)
                break
              case "error":
                assistantContent += `\n\nError: ${event.message}`
                setMessages((prev) => {
                  const updated = [...prev]
                  updated[updated.length - 1] = { role: "assistant", content: assistantContent }
                  return updated
                })
                break
            }
          } catch {
            // Skip malformed SSE lines
          }
        }
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev]
        if (updated.length > 0 && updated[updated.length - 1].role === "assistant") {
          updated[updated.length - 1] = {
            role: "assistant",
            content: "Sorry, something went wrong. Please try again.",
          }
        }
        return updated
      })
    } finally {
      setIsStreaming(false)
      setActiveTool(null)
    }
  }, [session, threadId, isStreaming])

  useEffect(() => {
    loadThread()
  }, [loadThread])

  useEffect(() => {
    const prompt = searchParams.get("prompt")
    if (prompt && !initialPromptHandled.current && session) {
      initialPromptHandled.current = true
      sendMessage(prompt)
    }
  }, [searchParams, session, sendMessage])

  return (
    <>
      <ChatHeader
        title={title}
        onMenuClick={() => {}}
        showMenu={!isDesktop}
      />
      <MessageList messages={messages} isStreaming={isStreaming} activeTool={activeTool} />
      <InputArea onSubmit={sendMessage} isLoading={isStreaming} />
    </>
  )
}
