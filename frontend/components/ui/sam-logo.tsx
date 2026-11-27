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
        <defs>
          <linearGradient id="sam-logo-grad" x1="0" y1="0" x2="100" y2="100" gradientUnits="userSpaceOnUse">
            <stop stopColor="#6366f1" />
            <stop offset="1" stopColor="#8b5cf6" />
          </linearGradient>
        </defs>
        <rect width="100" height="100" rx="22" fill="url(#sam-logo-grad)" />
        <path
          d="M62 30C62 30 55 30 50 30C40 30 34 36.5 34 43C34 49.5 40 53 50 55C60 57 66 60.5 66 67C66 73.5 60 80 50 80C45 80 38 80 38 80"
          stroke="white"
          strokeWidth="6"
          strokeLinecap="round"
        />
        <circle cx="62" cy="30" r="5" fill="white" opacity={0.9} />
        <circle cx="38" cy="80" r="5" fill="white" opacity={0.9} />
      </svg>
    </div>
  )
}
