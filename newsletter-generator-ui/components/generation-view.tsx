"use client"

import { useState, useRef, useCallback, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Loader2, Sparkles, AlertCircle, CheckCircle, ChevronDown } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { apiClient } from "@/lib/api"
import { getActivePlayers, getReviewRounds, getSearchProvider, getStrictDateFiltering } from "@/components/settings-modal"
import { DebugTerminal, DebugEvent } from "@/components/debug-terminal"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

interface GenerationViewProps {
  onBack: () => void
  onNewsletterGenerated: (id: string) => void
  onGenerationStart?: () => void
  isVisible?: boolean
}

interface StatusStep {
  id: string
  label: string
  status: 'pending' | 'active' | 'complete'
}

const allSteps: StatusStep[] = [
  { id: 'manager', label: 'Initializing run', status: 'pending' },
  { id: 'research_dc', label: 'Researching Data Centers', status: 'pending' },
  { id: 'research_cf', label: 'Researching Connectivity', status: 'pending' },
  { id: 'research_tw', label: 'Researching Towers', status: 'pending' },
  { id: 'review', label: 'Reviewing content', status: 'pending' },
  { id: 'editor', label: 'Editor finalising', status: 'pending' },
  { id: 'assemble', label: 'Assembling newsletter', status: 'pending' },
]

// Get filtered steps based on selected verticals
const getFilteredSteps = (selectedVerticals: {dataCenters: boolean, connectivity: boolean, towers: boolean}): StatusStep[] => {
  return allSteps.filter(step => {
    if (step.id === 'research_dc' && !selectedVerticals.dataCenters) return false
    if (step.id === 'research_cf' && !selectedVerticals.connectivity) return false
    if (step.id === 'research_tw' && !selectedVerticals.towers) return false
    return true
  })
}

export function GenerationView({ onBack, onNewsletterGenerated, onGenerationStart, isVisible = true }: GenerationViewProps) {
  const [isGenerating, setIsGenerating] = useState(false)
  const [steps, setSteps] = useState<StatusStep[]>(allSteps)
  const [error, setError] = useState<string | null>(null)
  const [debugEvents, setDebugEvents] = useState<DebugEvent[]>([])
  const debugIdCounter = useRef(0)
  const [lastNewsletterId, setLastNewsletterId] = useState<string | null>(null)
  const [readyNewsletterId, setReadyNewsletterId] = useState<string | null>(null)
  const [generatedVerticalIds, setGeneratedVerticalIds] = useState<string[]>([])
  const [debugSourcesOpen, setDebugSourcesOpen] = useState(false)
  const [debugSourcesLoading, setDebugSourcesLoading] = useState(false)
  const [debugSources, setDebugSources] = useState<Record<string, { title: string; url: string; publishDate?: string }[]>>({})

  const [verticals, setVerticals] = useState({
    dataCenters: true,
    connectivity: true,
    towers: true,
  })
  const [startDate, setStartDate] = useState(
    new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0]
  )
  const [endDate, setEndDate] = useState(
    new Date().toISOString().split("T")[0]
  )
  const [regions, setRegions] = useState<string[]>(["UK", "EU"])
  const { toast } = useToast()
  const abortControllerRef = useRef<AbortController | null>(null)

  const selectedVerticalIds = useMemo(() => ([
    ...(verticals.dataCenters ? ["data_centers"] : []),
    ...(verticals.connectivity ? ["connectivity_fibre"] : []),
    ...(verticals.towers ? ["towers_wireless"] : []),
  ]), [verticals])

  const verticalLabels: Record<string, string> = {
    data_centers: "Data Centers",
    connectivity_fibre: "Connectivity & Fibre",
    towers_wireless: "Towers & Wireless",
  }


  const updateStep = (stepId: string, status: 'active' | 'complete') => {
    const parallelSteps = ['research_dc', 'research_cf', 'research_tw']
    
    setSteps(prev => prev.map(step => {
      if (step.id === stepId) {
        return { ...step, status }
      }
      // Research steps can run in parallel - don't mark others complete
      if (status === 'active' && parallelSteps.includes(stepId) && parallelSteps.includes(step.id)) {
        return step // Keep other research steps as-is
      }
      // For non-research steps, mark previous active step complete
      if (status === 'active' && step.status === 'active' && step.id !== stepId && !parallelSteps.includes(step.id)) {
        return { ...step, status: 'complete' }
      }
      return step
    }))
  }

  const handleStatusUpdate = (step: string, message: string, status: 'start' | 'complete') => {
    // Map backend steps to frontend steps
    const stepMap: Record<string, string> = {
      'manager': 'manager',
      'research_data_centers': 'research_dc',
      'research_connectivity': 'research_cf',
      'research_towers': 'research_tw',
      'review': 'review',
      'editor': 'editor',
      'assemble': 'assemble',
    }
    
    const frontendStep = stepMap[step] || step
    // Map backend status to frontend status
    const frontendStatus = status === 'complete' ? 'complete' : 'active'
    updateStep(frontendStep, frontendStatus)
  }

  const handleDebugEvent = useCallback((category: string, content: string, metadata: Record<string, unknown>) => {
    const newEvent: DebugEvent = {
      id: `debug-${debugIdCounter.current++}`,
      timestamp: new Date(),
      category: category as DebugEvent['category'],
      content,
      metadata,
    }
    setDebugEvents(prev => [...prev, newEvent])
  }, [])

  const clearDebugEvents = useCallback(() => {
    setDebugEvents([])
    debugIdCounter.current = 0
  }, [])

  const loadDebugSources = useCallback(async (newsletterId: string, verticalIds: string[]) => {
    if (!newsletterId || verticalIds.length === 0) return
    setDebugSourcesLoading(true)
    try {
      const results: Record<string, { title: string; url: string; publishDate?: string }[]> = {}
      for (const sectionId of verticalIds) {
        try {
          const pack = await apiClient.getEvidencePack(newsletterId, sectionId)
          results[sectionId] = (pack.items || []).map((item) => ({
            title: item.title || "Source",
            url: item.url || "#",
            publishDate: item.data?.publish_date,
          }))
        } catch {
          results[sectionId] = []
        }
      }
      setDebugSources(results)
    } finally {
      setDebugSourcesLoading(false)
    }
  }, [])

  const handleGenerate = async () => {
    const hasVerticals = verticals.dataCenters || verticals.connectivity || verticals.towers
    if (!hasVerticals) {
      toast({
        title: "Error",
        description: "Select at least one sector to generate a newsletter",
        variant: "destructive",
      })
      return
    }

    setIsGenerating(true)
    setError(null)
    setLastNewsletterId(null)
    setReadyNewsletterId(null)
    setGeneratedVerticalIds([])
    clearDebugEvents() // Clear previous events
    // Filter steps based on selected verticals
    const filteredSteps = getFilteredSteps(verticals)
    setSteps(filteredSteps.map(s => ({ ...s, status: 'pending' as const })))
    onGenerationStart?.()

    try {
      const regionFocus = regions.length > 0 && regions.length < 6
        ? regions.join(", ")
        : null
      
      // Get settings
      const activePlayers = getActivePlayers()
      const reviewRounds = getReviewRounds()
      const searchProvider = getSearchProvider()
      const strictDateFiltering = getStrictDateFiltering()
      const verticalIds = selectedVerticalIds
      
      const response = await apiClient.generateNewsletterStreaming(
        { 
          time_window: { start: startDate, end: endDate },
          region_focus: regionFocus,
          max_review_rounds: reviewRounds, 
          active_players: activePlayers, 
          verticals: verticalIds,
          search_provider: searchProvider,
          strict_date_filtering: strictDateFiltering,
        },
        handleStatusUpdate,
        handleDebugEvent,
      )

      // Mark all steps complete
      setSteps(prev => prev.map(s => ({ ...s, status: 'complete' as const })))

      toast({
        title: "Newsletter generated",
        description: "Your newsletter is ready to view",
      })

      setLastNewsletterId(response.newsletter_id)
      setReadyNewsletterId(response.newsletter_id)
      setGeneratedVerticalIds(verticalIds)
      setDebugSources({})
      setDebugSourcesOpen(false)
    } catch (err) {
      // Fallback to non-streaming on error
      try {
        const regionFocus = regions.length > 0 && regions.length < 6
          ? regions.join(", ")
          : null
        const reviewRounds = getReviewRounds()
        const activePlayers = getActivePlayers()
        const searchProvider = getSearchProvider()
        const strictDateFiltering = getStrictDateFiltering()
        const verticalIds = selectedVerticalIds
        const filteredSteps = getFilteredSteps(verticals)
        
        // Simulate step progress for non-streaming
        for (const step of filteredSteps) {
          updateStep(step.id, 'active')
          await new Promise(r => setTimeout(r, 2000))
          updateStep(step.id, 'complete')
        }
        
        const response = await apiClient.generateNewsletter({
          time_window: { start: startDate, end: endDate },
          region_focus: regionFocus,
          max_review_rounds: reviewRounds,
          active_players: activePlayers,
          verticals: verticalIds,
          search_provider: searchProvider,
          strict_date_filtering: strictDateFiltering,
        })

        toast({
          title: "Newsletter generated",
          description: "Your newsletter is ready to view",
        })

        setLastNewsletterId(response.newsletter_id)
        setReadyNewsletterId(response.newsletter_id)
        setGeneratedVerticalIds(verticalIds)
        setDebugSources({})
        setDebugSourcesOpen(false)
      } catch (fallbackErr) {
        const message = fallbackErr instanceof Error ? fallbackErr.message : "Failed to generate newsletter"
        setError(message)
        toast({
          title: "Generation failed",
          description: message,
          variant: "destructive",
        })
      }
    } finally {
      setIsGenerating(false)
    }
  }

  const toggleRegion = (region: string) => {
    setRegions((prev) =>
      prev.includes(region)
        ? prev.filter((r) => r !== region)
        : [...prev, region]
    )
  }

  return (
    <div className="container mx-auto max-w-2xl px-4 py-12">
      {/* Page Header */}
      <header className="mb-10">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">
          Generate Newsletter
        </h1>
        <p className="mt-2 text-lg text-muted-foreground">
          Create a tailored weekly briefing on digital infrastructure.
        </p>
      </header>

      {/* Error Display */}
      {error && (
        <Card className="mb-6 border-destructive/50 bg-destructive/10">
          <CardContent className="flex items-center gap-3 py-4">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Newsletter Settings */}
      <div className="mb-10 space-y-6">
        {/* Time Window */}
        <div>
          <p className="mb-4 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
            Time Window
          </p>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="rounded-md border border-border/60 bg-card px-3 py-2 text-sm text-foreground transition-colors focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/20"
              disabled={isGenerating}
            />
            <span className="text-sm text-muted-foreground/60">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="rounded-md border border-border/60 bg-card px-3 py-2 text-sm text-foreground transition-colors focus:border-primary/50 focus:outline-none focus:ring-1 focus:ring-primary/20"
              disabled={isGenerating}
            />
          </div>
        </div>

        <div className="h-px bg-border/30" />

        {/* Verticals */}
        <div>
          <p className="mb-4 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
            Sector Coverage
          </p>
          <div className="flex flex-wrap gap-x-6 gap-y-3">
            <div className="flex items-center gap-2.5">
              <Checkbox
                id="dc"
                checked={verticals.dataCenters}
                onCheckedChange={(checked) =>
                  setVerticals((v) => ({ ...v, dataCenters: !!checked }))
                }
                disabled={isGenerating}
                className="border-border/60"
              />
              <label htmlFor="dc" className="text-sm text-foreground/90 cursor-pointer">
                Data Centers
              </label>
            </div>
            <div className="flex items-center gap-2.5">
              <Checkbox
                id="cf"
                checked={verticals.connectivity}
                onCheckedChange={(checked) =>
                  setVerticals((v) => ({ ...v, connectivity: !!checked }))
                }
                disabled={isGenerating}
                className="border-border/60"
              />
              <label htmlFor="cf" className="text-sm text-foreground/90 cursor-pointer">
                Connectivity & Fibre
              </label>
            </div>
            <div className="flex items-center gap-2.5">
              <Checkbox
                id="tw"
                checked={verticals.towers}
                onCheckedChange={(checked) =>
                  setVerticals((v) => ({ ...v, towers: !!checked }))
                }
                disabled={isGenerating}
                className="border-border/60"
              />
              <label htmlFor="tw" className="text-sm text-foreground/90 cursor-pointer">
                Towers & Wireless
              </label>
            </div>
          </div>
        </div>

        <div className="h-px bg-border/30" />

        {/* Regions */}
        <div>
          <p className="mb-4 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
            Geographic Focus
          </p>
          <div className="flex flex-wrap gap-2.5">
            {["UK", "EU", "US", "APAC", "MENA", "LATAM"].map((region) => (
              <button
                key={region}
                onClick={() => toggleRegion(region)}
                disabled={isGenerating}
                className={`rounded-full px-4 py-2 text-sm font-medium transition-all duration-150 ${
                  regions.includes(region)
                    ? "bg-primary text-primary-foreground shadow-sm"
                    : "bg-card text-muted-foreground border border-border/60 hover:border-border hover:text-foreground"
                } disabled:opacity-50`}
              >
                {region}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Progress Steps */}
      {isGenerating && (
        <div className="mb-8 rounded-lg border border-primary/20 bg-primary/5 p-5">
          <div className="space-y-3">
            {steps.map((step) => (
              <div key={step.id} className="flex items-center gap-3">
                {step.status === 'pending' && (
                  <div className="h-5 w-5 rounded-full border-2 border-muted" />
                )}
                {step.status === 'active' && (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                )}
                {step.status === 'complete' && (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                )}
                <span className={`text-sm ${
                  step.status === 'active' ? 'text-foreground font-medium' :
                  step.status === 'complete' ? 'text-muted-foreground' :
                  'text-muted-foreground/60'
                }`}>
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Debug Terminal - show during/after generation if there are events */}
      {(isGenerating || debugEvents.length > 0) && (
        <div className="mb-6">
          <DebugTerminal 
            events={debugEvents}
            onClear={clearDebugEvents}
            isGenerating={isGenerating}
          />
        </div>
      )}

      {lastNewsletterId && !isGenerating && (
        <div className="mb-8">
          <Collapsible
            open={debugSourcesOpen}
            onOpenChange={(open) => {
              setDebugSourcesOpen(open)
              if (open && Object.keys(debugSources).length === 0) {
                void loadDebugSources(lastNewsletterId, generatedVerticalIds.length > 0 ? generatedVerticalIds : selectedVerticalIds)
              }
            }}
          >
            <CollapsibleTrigger asChild>
              <button className="group flex items-center gap-2 text-xs text-muted-foreground/80 transition-colors hover:text-muted-foreground">
                <ChevronDown
                  className={`h-3.5 w-3.5 transition-transform duration-200 ${debugSourcesOpen ? "rotate-180" : ""}`}
                />
                <span>Debug sources</span>
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-3">
              <div className="rounded-md border border-border/60 bg-muted/20 px-4 py-3">
                {debugSourcesLoading ? (
                  <div className="text-xs text-muted-foreground">Loading sources...</div>
                ) : (
                  <div className="space-y-4">
                    {(generatedVerticalIds.length > 0 ? generatedVerticalIds : selectedVerticalIds).map((sectionId) => (
                      <div key={sectionId} className="space-y-2">
                        <div className="text-xs font-semibold uppercase tracking-wide text-muted-foreground/70">
                          {verticalLabels[sectionId] || sectionId}
                        </div>
                        <div className="space-y-2">
                          {(debugSources[sectionId] || []).length === 0 ? (
                            <div className="text-xs text-muted-foreground">No sources found.</div>
                          ) : (
                            (debugSources[sectionId] || []).map((item, idx) => {
                              const dateLabel = item.publishDate
                                ? new Date(item.publishDate).toLocaleDateString("en-GB", {
                                    day: "numeric",
                                    month: "short",
                                    year: "numeric",
                                  })
                                : "Unknown date";
                              return (
                                <div key={`${sectionId}-${idx}`} className="text-xs text-muted-foreground">
                                  <div className="font-medium text-foreground/90">
                                    {item.title}
                                  </div>
                                  <div className="flex flex-wrap gap-x-2 gap-y-1 text-muted-foreground/80">
                                    <span>{dateLabel}</span>
                                    {item.url && item.url !== "#" && (
                                      <>
                                        <span className="text-border">|</span>
                                        <a
                                          href={item.url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="text-primary hover:underline"
                                        >
                                          {item.url}
                                        </a>
                                      </>
                                    )}
                                  </div>
                                </div>
                              )
                            })
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>
      )}

      {/* Primary CTA */}
      <div className="flex flex-col items-end gap-3">
        {readyNewsletterId && !isGenerating && (
          <Button
            variant="outline"
            size="lg"
            onClick={() => {
              onNewsletterGenerated(readyNewsletterId)
            }}
            className="gap-2 px-6"
          >
            View Newsletter
          </Button>
        )}
        <Button
          onClick={handleGenerate}
          disabled={isGenerating || !(verticals.dataCenters || verticals.connectivity || verticals.towers)}
          size="lg"
          className="gap-2 px-6 shadow-sm transition-all duration-200 hover:shadow-md"
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Generate Newsletter
            </>
          )}
        </Button>
        <p className="text-xs text-muted-foreground/70">
          You can refine or edit sections after generation.
        </p>
      </div>

      {/* Preview Hint */}
      <div className="mt-16 border-t border-border/30 pt-8">
        <p className="text-center text-sm text-muted-foreground/60">
          Your newsletter will include high-level themes and key updates across selected sectors.
        </p>
      </div>
    </div>
  )
}
