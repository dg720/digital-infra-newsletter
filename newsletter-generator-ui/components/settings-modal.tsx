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
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Building2, Cable, Radio, Pencil, Check, X } from "lucide-react"

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

export type PlayerNames = {
  [vertical: string]: {
    [originalName: string]: string
  }
}

export type SearchProvider = "openai" | "tavily"

const STORAGE_KEY = "newsletter-player-settings"
const NAMES_STORAGE_KEY = "newsletter-player-names"
const REVIEW_ROUNDS_KEY = "newsletter-review-rounds"
const SEARCH_PROVIDER_KEY = "newsletter-search-provider"

export function getPlayerSettings(): PlayerSettings {
  if (typeof window === "undefined") return {}
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    try {
      const parsed = JSON.parse(stored)
      // Migrate old data: ensure all players have explicit true/false values
      let needsSave = false
      for (const [vertical, players] of Object.entries(DEFAULT_PLAYERS)) {
        if (!parsed[vertical]) {
          parsed[vertical] = {}
          needsSave = true
        }
        for (const player of players) {
          if (parsed[vertical][player] === undefined) {
            // Default to true for migration
            parsed[vertical][player] = true
            needsSave = true
          }
        }
      }
      if (needsSave) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(parsed))
      }
      return parsed
    } catch {
      // Fall through to defaults
    }
  }
  // Default: all players enabled for all verticals, save to localStorage
  const defaults: PlayerSettings = {}
  for (const [vertical, players] of Object.entries(DEFAULT_PLAYERS)) {
    defaults[vertical] = {}
    for (const player of players) {
      defaults[vertical][player] = true
    }
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(defaults))
  return defaults
}

export function getPlayerNames(): PlayerNames {
  if (typeof window === "undefined") return {}
  const stored = localStorage.getItem(NAMES_STORAGE_KEY)
  if (stored) {
    try {
      return JSON.parse(stored)
    } catch {
      return {}
    }
  }
  return {}
}

export function getReviewRounds(): number {
  if (typeof window === "undefined") return 2
  const stored = localStorage.getItem(REVIEW_ROUNDS_KEY)
  if (stored) {
    try {
      return parseInt(stored, 10) || 2
    } catch {
      return 2
    }
  }
  return 2
}

export function getSearchProvider(): SearchProvider {
  if (typeof window === "undefined") return "openai"
  const stored = localStorage.getItem(SEARCH_PROVIDER_KEY)
  if (stored === "tavily" || stored === "openai") {
    return stored
  }
  return "openai"
}

export function getActivePlayers(): { [vertical: string]: string[] } {
  const settings = getPlayerSettings()
  const names = getPlayerNames()
  const result: { [vertical: string]: string[] } = {}
  
  for (const [vertical, players] of Object.entries(DEFAULT_PLAYERS)) {
    const verticalSettings = settings[vertical] || {}
    const verticalNames = names[vertical] || {}
    result[vertical] = players
      .filter(player => {
        // Only include if explicitly set to true
        // If no settings exist for this vertical, include none (user hasn't configured yet)
        // If settings exist but player not in it, treat as disabled
        return verticalSettings[player] === true
      })
      .map(player => {
        // Use custom name if set, otherwise original
        return verticalNames[player] || player
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
  const [names, setNames] = useState<PlayerNames>({})
  const [reviewRounds, setReviewRounds] = useState(2)
  const [searchProvider, setSearchProvider] = useState<SearchProvider>("openai")
  const [editingPlayer, setEditingPlayer] = useState<{vertical: string, player: string} | null>(null)
  const [editValue, setEditValue] = useState("")

  useEffect(() => {
    setSettings(getPlayerSettings())
    setNames(getPlayerNames())
    setReviewRounds(getReviewRounds())
    setSearchProvider(getSearchProvider())
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

  const handleToggleAll = (vertical: string, enabled: boolean) => {
    const players = DEFAULT_PLAYERS[vertical as keyof typeof DEFAULT_PLAYERS] || []
    const newVerticalSettings: { [player: string]: boolean } = {}
    players.forEach(player => {
      newVerticalSettings[player] = enabled
    })
    const newSettings = {
      ...settings,
      [vertical]: newVerticalSettings,
    }
    setSettings(newSettings)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newSettings))
  }

  const isPlayerEnabled = (vertical: string, player: string): boolean => {
    // Match getActivePlayers: only true if explicitly true
    return settings[vertical]?.[player] === true
  }

  const getEnabledCount = (vertical: string): number => {
    const players = DEFAULT_PLAYERS[vertical as keyof typeof DEFAULT_PLAYERS] || []
    return players.filter(p => isPlayerEnabled(vertical, p)).length
  }

  const areAllEnabled = (vertical: string): boolean => {
    const players = DEFAULT_PLAYERS[vertical as keyof typeof DEFAULT_PLAYERS] || []
    return players.every(p => isPlayerEnabled(vertical, p))
  }

  const getDisplayName = (vertical: string, player: string): string => {
    return names[vertical]?.[player] || player
  }

  const startEditing = (vertical: string, player: string) => {
    setEditingPlayer({ vertical, player })
    setEditValue(getDisplayName(vertical, player))
  }

  const cancelEditing = () => {
    setEditingPlayer(null)
    setEditValue("")
  }

  const saveEditing = () => {
    if (!editingPlayer) return
    
    const { vertical, player } = editingPlayer
    const newNames = {
      ...names,
      [vertical]: {
        ...(names[vertical] || {}),
        [player]: editValue.trim() || player, // Fall back to original if empty
      },
    }
    setNames(newNames)
    localStorage.setItem(NAMES_STORAGE_KEY, JSON.stringify(newNames))
    setEditingPlayer(null)
    setEditValue("")
  }

  const handleReviewRoundsChange = (value: number) => {
    const rounds = Math.max(1, Math.min(5, value))
    setReviewRounds(rounds)
    localStorage.setItem(REVIEW_ROUNDS_KEY, rounds.toString())
  }

  const handleSearchProviderChange = (provider: SearchProvider) => {
    setSearchProvider(provider)
    localStorage.setItem(SEARCH_PROVIDER_KEY, provider)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Research Configuration</DialogTitle>
          <DialogDescription>
            Configure research settings, major players, and review parameters.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-8 py-4">
          {/* Review Rounds Setting */}
          <div className="rounded-lg border border-border p-4 bg-muted/30">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-sm font-medium">Review Rounds</Label>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Number of review iterations before finalizing (1-5)
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={() => handleReviewRoundsChange(reviewRounds - 1)}
                  disabled={reviewRounds <= 1}
                >
                  -
                </Button>
                <Input
                  type="number"
                  min={1}
                  max={5}
                  value={reviewRounds}
                  onChange={(e) => handleReviewRoundsChange(parseInt(e.target.value) || 2)}
                  className="w-16 h-8 text-center"
                />
                <Button
                  variant="outline"
                  size="sm"
                  className="h-8 w-8 p-0"
                  onClick={() => handleReviewRoundsChange(reviewRounds + 1)}
                  disabled={reviewRounds >= 5}
                >
                  +
                </Button>
              </div>
            </div>
          </div>

          {/* Search Provider */}
          <div className="rounded-lg border border-border p-4 bg-muted/30">
            <div className="flex items-center justify-between gap-4">
              <div>
                <Label className="text-sm font-medium">Search Provider</Label>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Default uses OpenAI web search for lower cost. Switch to Tavily if needed.
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant={searchProvider === "openai" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleSearchProviderChange("openai")}
                >
                  OpenAI
                </Button>
                <Button
                  variant={searchProvider === "tavily" ? "default" : "outline"}
                  size="sm"
                  onClick={() => handleSearchProviderChange("tavily")}
                >
                  Tavily
                </Button>
              </div>
            </div>
          </div>

          <div className="h-px bg-border" />

          {/* Major Players Configuration */}
          <div>
            <h3 className="text-sm font-medium mb-4">Major Players</h3>
            <p className="text-xs text-muted-foreground mb-6">
              Toggle which companies to research. Fewer players = faster research. Click the edit icon to rename.
            </p>

            {Object.entries(DEFAULT_PLAYERS).map(([vertical, players], idx) => {
              const config = verticalConfig[vertical as keyof typeof verticalConfig]
              const Icon = config?.icon || Building2
              const enabledCount = getEnabledCount(vertical)
              const allEnabled = areAllEnabled(vertical)

              return (
                <div key={vertical}>
                  {idx > 0 && <div className="h-px bg-border my-6" />}
                  
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-primary" />
                        <h4 className="font-medium">{config?.title || vertical}</h4>
                        <Badge variant="secondary" className="ml-2 text-xs">
                          {enabledCount}/{players.length} active
                        </Badge>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleToggleAll(vertical, !allEnabled)}
                        className="text-xs"
                      >
                        {allEnabled ? "Deselect All" : "Select All"}
                      </Button>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-3 pl-6">
                      {players.map((player) => {
                        const isEditing = editingPlayer?.vertical === vertical && editingPlayer?.player === player
                        
                        return (
                          <div
                            key={player}
                            className="flex items-center justify-between gap-2 rounded-md border px-3 py-2.5"
                          >
                            {isEditing ? (
                              <div className="flex items-center gap-2 flex-1">
                                <Input
                                  value={editValue}
                                  onChange={(e) => setEditValue(e.target.value)}
                                  className="h-7 text-sm"
                                  autoFocus
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') saveEditing()
                                    if (e.key === 'Escape') cancelEditing()
                                  }}
                                />
                                <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={saveEditing}>
                                  <Check className="h-3.5 w-3.5 text-green-500" />
                                </Button>
                                <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={cancelEditing}>
                                  <X className="h-3.5 w-3.5 text-destructive" />
                                </Button>
                              </div>
                            ) : (
                              <>
                                <div className="flex items-center gap-2 flex-1 min-w-0">
                                  <Label
                                    htmlFor={`${vertical}-${player}`}
                                    className="text-sm font-normal cursor-pointer truncate"
                                  >
                                    {getDisplayName(vertical, player)}
                                  </Label>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-6 w-6 p-0 opacity-50 hover:opacity-100"
                                    onClick={() => startEditing(vertical, player)}
                                  >
                                    <Pencil className="h-3 w-3" />
                                  </Button>
                                </div>
                                <Switch
                                  id={`${vertical}-${player}`}
                                  checked={isPlayerEnabled(vertical, player)}
                                  onCheckedChange={(checked) =>
                                    handleToggle(vertical, player, checked)
                                  }
                                />
                              </>
                            )}
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
