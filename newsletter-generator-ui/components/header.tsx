"use client"

import { useState } from "react"
import { Newspaper, ArrowLeft, Settings } from "lucide-react"
import { Button } from "@/components/ui/button"
import { SettingsModal } from "@/components/settings-modal"
import type { ViewState } from "@/app/page"

interface HeaderProps {
  view: ViewState
  onBackToDashboard: () => void
  onStartGeneration: () => void
}

export function Header({ view, onBackToDashboard, onStartGeneration }: HeaderProps) {
  const [settingsOpen, setSettingsOpen] = useState(false)

  return (
    <>
      <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur-sm">
        <div className="container mx-auto max-w-4xl px-4">
          <div className="flex h-14 items-center justify-between">
            <div className="flex items-center gap-3">
              {view.type !== "dashboard" && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onBackToDashboard}
                  className="mr-2 gap-2 text-muted-foreground hover:text-foreground"
                >
                  <ArrowLeft className="h-4 w-4" />
                  <span className="hidden sm:inline">Library</span>
                </Button>
              )}
              <button 
                onClick={onBackToDashboard}
                className="flex items-center gap-2.5 transition-opacity hover:opacity-80"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                  <Newspaper className="h-4 w-4 text-primary-foreground" />
                </div>
                <span className="text-base font-semibold tracking-tight text-foreground">
                  Digital Infra Newsletter
                </span>
              </button>
            </div>
            
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSettingsOpen(true)}
              className="gap-1.5 text-muted-foreground hover:text-foreground"
            >
              <Settings className="h-4 w-4" />
              <span className="text-sm">Config</span>
            </Button>
          </div>
        </div>
      </header>

      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  )
}
