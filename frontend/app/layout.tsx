import type { Metadata } from "next"
import { ThemeProvider } from "next-themes"
import "./globals.css"

export const metadata: Metadata = {
  title: "SAM AI",
  description: "Your intelligent AI assistant",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen antialiased">
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
