"use client"

import { Search, FileText, Code, Sparkles } from "lucide-react"
import { SamLogo } from "@/components/ui/sam-logo"

const SUGGESTIONS = [
  {
    icon: Search,
    label: "Search the web",
    prompt: "Search the web for today's top tech news",
  },
  {
    icon: FileText,
    label: "Analyze a PDF",
    prompt: "Upload a PDF and I'll summarize the key points",
  },
  {
    icon: Code,
    label: "Debug code",
    prompt: "Help me debug a Python error I'm running into",
  },
  {
    icon: Sparkles,
    label: "Brainstorm ideas",
    prompt: "Help me brainstorm creative project ideas",
  },
]

interface WelcomeScreenProps {
  onSuggestionClick: (text: string) => void
}

export function WelcomeScreen({ onSuggestionClick }: WelcomeScreenProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 px-4 sm:gap-8">
      <div className="flex flex-col items-center gap-3 sm:gap-4">
        <SamLogo size="lg" className="h-16 w-16 sm:h-24 sm:w-24" />
        <div className="text-center">
          <h2 className="text-xl font-semibold sm:text-2xl">Welcome to <span className="sam-gradient-text">SAM AI</span></h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Your intelligent assistant — search, analyze, code, and create.
          </p>
        </div>
      </div>

      <div className="grid w-full max-w-xl grid-cols-1 gap-2.5 sm:grid-cols-2 sm:gap-3">
        {SUGGESTIONS.map(({ icon: Icon, label, prompt }) => (
          <button
            key={label}
            className="group flex items-start gap-3 rounded-xl border border-border/50 bg-card p-3 text-left transition-all hover:border-primary/40 hover:bg-accent hover:shadow-sm active:scale-[0.98] sm:p-4"
            onClick={() => onSuggestionClick(prompt)}
          >
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary/20">
              <Icon className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-medium">{label}</div>
              <div className="mt-0.5 text-xs text-muted-foreground line-clamp-2">{prompt}</div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
