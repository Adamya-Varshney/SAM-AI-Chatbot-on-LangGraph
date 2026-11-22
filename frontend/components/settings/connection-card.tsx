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
    <div className="flex items-center justify-between rounded-lg border p-4">
      <div>
        <p className="font-medium capitalize">{provider}</p>
        <p className="text-sm text-muted-foreground">
          {connected ? "Connected" : "Not connected"}
        </p>
      </div>
      {connected ? (
        <Button variant="outline" size="sm" onClick={onDisconnect} className="gap-2">
          <Unplug className="h-4 w-4" />
          Disconnect
        </Button>
      ) : (
        <Button variant="outline" size="sm" onClick={onConnect} className="gap-2">
          <ExternalLink className="h-4 w-4" />
          Connect
        </Button>
      )}
    </div>
  )
}
