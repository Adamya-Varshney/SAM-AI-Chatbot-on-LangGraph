"use client"

import { cn } from "@/lib/utils"

interface SamLogoProps {
  size?: "sm" | "md" | "lg"
  className?: string
}

export function SamLogo({ size = "md", className }: SamLogoProps) {
  const sizes = {
    sm: "h-10 w-10",
    md: "h-16 w-16",
    lg: "h-24 w-24",
  }

  const textSizes = {
    sm: "text-lg",
    md: "text-2xl",
    lg: "text-4xl",
  }

  return (
    <div
      className={cn(
        "flex items-center justify-center rounded-2xl bg-gradient-to-br from-primary via-primary/80 to-primary/60 text-primary-foreground font-bold shadow-lg",
        sizes[size],
        className,
      )}
    >
      <span className={textSizes[size]}>S</span>
    </div>
  )
}
