"use client"

import { useEffect, useRef } from "react"
import { MessageBubble } from "./message-bubble"
import { ToolIndicator } from "./tool-indicator"

interface Message {
  role: "user" | "assistant"
  content: string
}

interface MessageListProps {
  messages: Message[]
  isStreaming: boolean
  activeTool: string | null
}

export function MessageList({ messages, isStreaming, activeTool }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, activeTool])

  return (
    <div className="flex-1 overflow-y-auto overscroll-contain">
      <div className="mx-auto max-w-3xl">
        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            role={msg.role}
            content={msg.content}
            isStreaming={isStreaming && i === messages.length - 1 && msg.role === "assistant"}
          />
        ))}
        {activeTool && (
          <div className="px-3 py-2 sm:px-4">
            <ToolIndicator label={activeTool} />
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
