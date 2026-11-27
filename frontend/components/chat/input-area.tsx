"use client"

import { useRef, useState, useCallback } from "react"
import { Send, Paperclip, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

interface InputAreaProps {
  onSubmit: (message: string, file?: File) => void
  isLoading: boolean
}

export function InputArea({ onSubmit, isLoading }: InputAreaProps) {
  const [input, setInput] = useState("")
  const [attachedFile, setAttachedFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSubmit = () => {
    if (!input.trim() && !attachedFile) return
    onSubmit(input.trim(), attachedFile || undefined)
    setInput("")
    setAttachedFile(null)
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    const el = e.target
    el.style.height = "auto"
    el.style.height = Math.min(el.scrollHeight, 200) + "px"
  }

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file?.type === "application/pdf") {
      setAttachedFile(file)
    }
  }, [])

  return (
    <div
      className={cn(
        "border-t bg-background p-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))] sm:p-4 sm:pb-[calc(1rem+env(safe-area-inset-bottom))]",
        dragOver && "ring-2 ring-primary ring-inset",
      )}
      onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {attachedFile && (
        <div className="mb-2 flex items-center gap-2 rounded-md bg-muted px-3 py-1.5 text-sm">
          <Paperclip className="h-4 w-4 shrink-0" />
          <span className="min-w-0 truncate">{attachedFile.name}</span>
          <Button
            variant="ghost"
            size="icon"
            className="ml-auto h-5 w-5 shrink-0"
            onClick={() => setAttachedFile(null)}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      )}

      <div className="mx-auto flex max-w-3xl items-end gap-1.5 sm:gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) setAttachedFile(file)
          }}
        />
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9 shrink-0 sm:h-10 sm:w-10"
          onClick={() => fileInputRef.current?.click()}
          aria-label="Attach PDF"
        >
          <Paperclip className="h-4 w-4 sm:h-5 sm:w-5" />
        </Button>

        <textarea
          ref={textareaRef}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Message SAM AI..."
          rows={1}
          className="min-h-[40px] flex-1 resize-none rounded-xl border border-input bg-background px-3 py-2.5 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:border-primary/40"
        />

        <Button
          size="icon"
          className="h-9 w-9 shrink-0 sam-gradient text-white hover:opacity-90 disabled:opacity-50 sm:h-10 sm:w-10"
          onClick={handleSubmit}
          disabled={isLoading || (!input.trim() && !attachedFile)}
          aria-label="Send message"
        >
          <Send className="h-4 w-4 sm:h-5 sm:w-5" />
        </Button>
      </div>
    </div>
  )
}
