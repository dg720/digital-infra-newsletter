"use client"

import { useState, useEffect, useCallback } from "react"
import { Header } from "@/components/header"
import { DashboardView } from "@/components/dashboard-view"
import { NewsletterReadingView } from "@/components/newsletter-reading-view"
import { GenerationView } from "@/components/generation-view"
import { Toaster } from "@/components/ui/toaster"
import { fetchNewsletterList, type NewsletterListItem } from "@/lib/api"

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

export default function HomeClient() {
  const [view, setView] = useState<ViewState>({ type: "dashboard" })

  // Cached newsletter list - shared across views
  const [newsletters, setNewsletters] = useState<NewsletterListItem[]>([])
  const [isLoadingNewsletters, setIsLoadingNewsletters] = useState(true)
  const [newsletterError, setNewsletterError] = useState<string | null>(null)

  // Track if generation is in progress (to keep component alive)
  const [isGenerating, setIsGenerating] = useState(false)
  const [hasVisitedGenerate, setHasVisitedGenerate] = useState(false)

  // Load newsletters once on mount
  const loadNewsletters = useCallback(async () => {
    setIsLoadingNewsletters(true)
    setNewsletterError(null)
    try {
      const data = await fetchNewsletterList()
      setNewsletters(data)
    } catch (err) {
      setNewsletterError(err instanceof Error ? err.message : "Failed to load newsletters")
    } finally {
      setIsLoadingNewsletters(false)
    }
  }, [])

  useEffect(() => {
    loadNewsletters()
  }, [loadNewsletters])

  const handleOpenNewsletter = (id: string) => {
    setView({ type: "reading", newsletterId: id })
  }

  const handleBackToDashboard = () => {
    setView({ type: "dashboard" })
    // Refresh newsletter list when coming back (in background)
    loadNewsletters()
  }

  const handleStartGeneration = () => {
    setHasVisitedGenerate(true)
    setView({ type: "generate" })
  }

  const handleNewsletterGenerated = (id: string) => {
    setIsGenerating(false)
    // Refresh newsletter list to include the new one
    loadNewsletters()
    setView({ type: "reading", newsletterId: id })
  }

  const handleGenerationStart = () => {
    setIsGenerating(true)
  }

  return (
    <div className="min-h-screen bg-background">
      <Header
        view={view}
        onBackToDashboard={handleBackToDashboard}
        onStartGeneration={handleStartGeneration}
      />
      <main>
        {/* Dashboard - always rendered after first load, hidden when not active */}
        <div className={view.type === "dashboard" ? "" : "hidden"}>
          <DashboardView
            onOpenNewsletter={handleOpenNewsletter}
            onStartGeneration={handleStartGeneration}
            newsletters={newsletters}
            isLoading={isLoadingNewsletters}
            error={newsletterError}
            onRefresh={loadNewsletters}
          />
        </div>

        {/* Generation - keep mounted if visited or generating (preserves progress) */}
        {(hasVisitedGenerate || isGenerating) && (
          <div className={view.type === "generate" ? "" : "hidden"}>
            <GenerationView
              onBack={handleBackToDashboard}
              onNewsletterGenerated={handleNewsletterGenerated}
              onGenerationStart={handleGenerationStart}
              isVisible={view.type === "generate"}
            />
          </div>
        )}

        {/* Reading - only render when active */}
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
