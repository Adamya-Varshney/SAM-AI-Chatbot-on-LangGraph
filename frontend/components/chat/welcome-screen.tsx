"use client"

import { Bot } from "lucide-react"
import { Button } from "@/components/ui/button"

const SUGGESTIONS = [
  "Search the web for today's top tech news",
  "Help me debug a Python error",
  "Summarize this PDF for me",
  "What's the weather in my area?",
]

interface WelcomeScreenProps {
  onSuggestionClick: (text: string) => void
}

export function WelcomeScreen({ onSuggestionClick }: WelcomeScreenProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 px-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
        <Bot className="h-8 w-8 text-primary" />
      </div>
      <h2 className="text-2xl font-semibold">How can I help you today?</h2>
      <div className="grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
        {SUGGESTIONS.map((text) => (
          <Button
            key={text}
            variant="outline"
            className="h-auto whitespace-normal p-3 text-left text-sm"
            onClick={() => onSuggestionClick(text)}
          >
            {text}
          </Button>
        ))}
      </div>
    </div>
  )
}
