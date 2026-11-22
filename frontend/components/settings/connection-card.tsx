"use client"

import { ExternalLink, Unplug } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ConnectionCardProps {
  provider: string
  connected: boolean
  onConnect: () => void
  onDisconnect: () => void
}

export function ConnectionCard({ provider, connected, onConnect, onDisconnect }: ConnectionCardProps) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border p-3 sm:p-4">
      <div className="min-w-0">
        <p className="font-medium capitalize">{provider}</p>
        <p className="text-sm text-muted-foreground">
          {connected ? "Connected" : "Not connected"}
        </p>
      </div>
      {connected ? (
        <Button variant="outline" size="sm" onClick={onDisconnect} className="shrink-0 gap-1.5 sm:gap-2">
          <Unplug className="h-4 w-4" />
          <span className="hidden xs:inline sm:inline">Disconnect</span>
        </Button>
      ) : (
        <Button variant="outline" size="sm" onClick={onConnect} className="shrink-0 gap-1.5 sm:gap-2">
          <ExternalLink className="h-4 w-4" />
          <span>Connect</span>
        </Button>
      )}
    </div>
  )
}
