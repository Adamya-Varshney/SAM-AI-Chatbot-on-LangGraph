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

  return (
    <div className={cn(sizes[size], className)}>
      <svg
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="h-full w-full"
      >
        <rect x="15" y="65" width="70" height="22" rx="11" fill="#7B2D26" transform="rotate(-2.5 50 76)" />
        <rect x="22" y="41" width="56" height="20" rx="10" fill="#6B2D4A" transform="rotate(1.8 50 51)" />
        <rect x="30" y="20" width="40" height="18" rx="9" fill="#7c3aed" transform="rotate(-1.2 50 29)" />
      </svg>
    </div>
  )
}
