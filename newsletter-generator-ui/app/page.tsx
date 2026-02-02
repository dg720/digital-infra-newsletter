"use client"

import { useState } from "react"
import { Header } from "@/components/header"
import { DashboardView } from "@/components/dashboard-view"
import { NewsletterReadingView } from "@/components/newsletter-reading-view"
import { GenerationView } from "@/components/generation-view"
import { Toaster } from "@/components/ui/toaster"

export interface Newsletter {
  id: string
  title: string
  date: string
  timeWindow: { start: string; end: string }
  voiceProfile: string
  verticals: string[]
  regions: string[]
  sections: {
    dataCenters: NewsletterSection
    connectivity: NewsletterSection
    towers: NewsletterSection
  }
}

export interface NewsletterSection {
  bigPicture: string
  bullets: Array<{
    text: string
    evidenceId: string
  }>
  evidence: Array<{
    id: string
    title: string
    source: string
    url: string
  }>
}

export type ViewState = 
  | { type: "dashboard" }
  | { type: "generate" }
  | { type: "reading"; newsletterId: string }

export default function Home() {
  const [view, setView] = useState<ViewState>({ type: "dashboard" })

  const handleOpenNewsletter = (id: string) => {
    setView({ type: "reading", newsletterId: id })
  }

  const handleBackToDashboard = () => {
    setView({ type: "dashboard" })
  }

  const handleStartGeneration = () => {
    setView({ type: "generate" })
  }

  return (
    <div className="min-h-screen bg-background">
      <Header 
        view={view} 
        onBackToDashboard={handleBackToDashboard}
        onStartGeneration={handleStartGeneration}
      />
      <main>
        {view.type === "dashboard" && (
          <DashboardView 
            onOpenNewsletter={handleOpenNewsletter}
            onStartGeneration={handleStartGeneration}
          />
        )}
        {view.type === "generate" && (
          <GenerationView 
            onBack={handleBackToDashboard}
            onNewsletterGenerated={(id) => setView({ type: "reading", newsletterId: id })}
          />
        )}
        {view.type === "reading" && (
          <NewsletterReadingView 
            newsletterId={view.newsletterId}
            onBack={handleBackToDashboard}
          />
        )}
      </main>
      <Toaster />
    </div>
  )
}
