"use client"

import { useState, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Building2, Cable, Radio } from "lucide-react"

interface SettingsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

// Default players per vertical (matches backend constants.py)
const DEFAULT_PLAYERS = {
  data_centers: [
    "Equinix",
    "Digital Realty",
    "CyrusOne",
    "QTS Data Centers",
    "NTT Global Data Centers",
    "Iron Mountain Data Centers",
    "Switch",
    "STACK Infrastructure",
    "Google Cloud",
    "Amazon Web Services (AWS)",
  ],
  connectivity_fibre: [
    "Lumen Technologies",
    "Zayo",
    "Crown Castle Fiber",
    "Colt Technology Services",
    "euNetworks",
    "CityFibre",
    "Openreach",
    "Telxius",
    "Sparkle (Telecom Italia Sparkle)",
    "Subsea7",
  ],
  towers_wireless: [
    "American Tower",
    "Cellnex Telecom",
    "Vantage Towers",
    "SBA Communications",
    "IHS Towers",
    "Indus Towers",
    "Crown Castle",
    "Phoenix Tower International",
    "Helios Towers",
    "DigitalBridge",
  ],
}

export type PlayerSettings = {
  [vertical: string]: {
    [player: string]: boolean
  }
}

const STORAGE_KEY = "newsletter-player-settings"

export function getPlayerSettings(): PlayerSettings {
  if (typeof window === "undefined") return {}
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    try {
      return JSON.parse(stored)
    } catch {
      return {}
    }
  }
  return {}
}

export function getActivePlayers(): { [vertical: string]: string[] } {
  const settings = getPlayerSettings()
  const result: { [vertical: string]: string[] } = {}
  
  for (const [vertical, players] of Object.entries(DEFAULT_PLAYERS)) {
    const verticalSettings = settings[vertical] || {}
    result[vertical] = players.filter(player => {
      // Default to enabled if not set
      return verticalSettings[player] !== false
    })
  }
  
  return result
}

const verticalConfig = {
  data_centers: { title: "Data Centers", icon: Building2 },
  connectivity_fibre: { title: "Connectivity & Fibre", icon: Cable },
  towers_wireless: { title: "Towers & Wireless", icon: Radio },
}

export function SettingsModal({ open, onOpenChange }: SettingsModalProps) {
  const [settings, setSettings] = useState<PlayerSettings>({})

  useEffect(() => {
    setSettings(getPlayerSettings())
  }, [open])

  const handleToggle = (vertical: string, player: string, enabled: boolean) => {
    const newSettings = {
      ...settings,
      [vertical]: {
        ...(settings[vertical] || {}),
        [player]: enabled,
      },
    }
    setSettings(newSettings)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newSettings))
  }

  const isPlayerEnabled = (vertical: string, player: string): boolean => {
    return settings[vertical]?.[player] !== false
  }

  const getEnabledCount = (vertical: string): number => {
    const players = DEFAULT_PLAYERS[vertical as keyof typeof DEFAULT_PLAYERS] || []
    return players.filter(p => isPlayerEnabled(vertical, p)).length
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Research Settings</DialogTitle>
          <DialogDescription>
            Toggle which major players to search for. Fewer players = faster research.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {Object.entries(DEFAULT_PLAYERS).map(([vertical, players]) => {
            const config = verticalConfig[vertical as keyof typeof verticalConfig]
            const Icon = config?.icon || Building2
            const enabledCount = getEnabledCount(vertical)

            return (
              <div key={vertical} className="space-y-3">
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 text-primary" />
                  <h3 className="font-medium">{config?.title || vertical}</h3>
                  <Badge variant="secondary" className="ml-auto text-xs">
                    {enabledCount}/{players.length} active
                  </Badge>
                </div>
                
                <div className="grid grid-cols-2 gap-2 pl-6">
                  {players.map((player) => (
                    <div
                      key={player}
                      className="flex items-center justify-between gap-2 rounded-md border px-3 py-2"
                    >
                      <Label
                        htmlFor={`${vertical}-${player}`}
                        className="text-sm font-normal cursor-pointer flex-1"
                      >
                        {player}
                      </Label>
                      <Switch
                        id={`${vertical}-${player}`}
                        checked={isPlayerEnabled(vertical, player)}
                        onCheckedChange={(checked) =>
                          handleToggle(vertical, player, checked)
                        }
                      />
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </DialogContent>
    </Dialog>
  )
}
