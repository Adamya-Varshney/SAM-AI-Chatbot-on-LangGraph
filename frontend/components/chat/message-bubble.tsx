"use client"

import { useState } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Copy, Check, User, Bot } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

interface MessageBubbleProps {
  role: "user" | "assistant"
  content: string
  isStreaming?: boolean
}

export function MessageBubble({ role, content, isStreaming }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className={cn("group flex gap-2 px-3 py-3 sm:gap-3 sm:px-4 sm:py-4", role === "user" && "flex-row-reverse")}>
      <div
        className={cn(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full sm:h-8 sm:w-8",
          role === "user" ? "sam-gradient text-white" : "bg-accent text-primary",
        )}
      >
        {role === "user" ? <User className="h-3.5 w-3.5 sm:h-4 sm:w-4" /> : <Bot className="h-3.5 w-3.5 sm:h-4 sm:w-4" />}
      </div>

      <div className={cn("flex min-w-0 flex-col gap-1", role === "user" ? "items-end" : "items-start", "max-w-[85%] md:max-w-[75%]")}>
        <div
          className={cn(
            "overflow-hidden rounded-2xl px-3 py-2 sm:px-4 sm:py-2.5",
            role === "user"
              ? "sam-gradient text-white"
              : "bg-muted",
          )}
        >
          {role === "assistant" ? (
            <div className="prose prose-sm dark:prose-invert max-w-none break-words [&_pre]:overflow-x-auto [&_pre]:max-w-full [&_code]:break-words [&_table]:block [&_table]:overflow-x-auto">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
              {isStreaming && <span className="inline-block h-4 w-1 animate-pulse bg-current" />}
            </div>
          ) : (
            <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
          )}
        </div>

        {role === "assistant" && !isStreaming && content && (
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 group-hover:opacity-100 touch-show"
            onClick={handleCopy}
            aria-label="Copy message"
          >
            {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          </Button>
        )}
      </div>
    </div>
  )
}
