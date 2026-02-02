"use client"

import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { ChevronDown, Loader2, Sparkles, AlertCircle, CheckCircle } from "lucide-react"
import { useToast } from "@/hooks/use-toast"
import { apiClient } from "@/lib/api"

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

const initialSteps: StatusStep[] = [
  { id: 'manager', label: 'Parsing request', status: 'pending' },
  { id: 'research_dc', label: 'Researching Data Centers', status: 'pending' },
  { id: 'research_cf', label: 'Researching Connectivity', status: 'pending' },
  { id: 'research_tw', label: 'Researching Towers', status: 'pending' },
  { id: 'review', label: 'Reviewing content', status: 'pending' },
  { id: 'editor', label: 'Editor finalising', status: 'pending' },
  { id: 'assemble', label: 'Assembling newsletter', status: 'pending' },
]

export function GenerationView({ onBack, onNewsletterGenerated, onGenerationStart, isVisible = true }: GenerationViewProps) {
  const [prompt, setPrompt] = useState("")
  const [isAdvancedOpen, setIsAdvancedOpen] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [steps, setSteps] = useState<StatusStep[]>(initialSteps)
  const [error, setError] = useState<string | null>(null)

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

  const buildPrompt = () => {
    let fullPrompt = prompt.trim()

    if (!fullPrompt.toLowerCase().includes("week") && 
        !fullPrompt.toLowerCase().includes("day") && 
        !fullPrompt.toLowerCase().includes("month")) {
      fullPrompt += ` for the period from ${startDate} to ${endDate}`
    }

    const selectedVerticals = []
    if (verticals.dataCenters) selectedVerticals.push("data centres")
    if (verticals.connectivity) selectedVerticals.push("connectivity and fibre")
    if (verticals.towers) selectedVerticals.push("towers and wireless")
    
    if (selectedVerticals.length < 3 && selectedVerticals.length > 0) {
      fullPrompt += `. Focus on ${selectedVerticals.join(" and ")}`
    }

    if (regions.length > 0 && regions.length < 6) {
      fullPrompt += `. Geographic focus: ${regions.join(", ")}`
    }

    return fullPrompt
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

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      toast({
        title: "Error",
        description: "Please enter a description for your newsletter",
        variant: "destructive",
      })
      return
    }

    setIsGenerating(true)
    setError(null)
    setSteps(initialSteps.map(s => ({ ...s, status: 'pending' as const })))
    onGenerationStart?.()

    try {
      const fullPrompt = buildPrompt()
      
      // Try streaming first, fall back to regular if not available
      const response = await apiClient.generateNewsletterStreaming(
        { prompt: fullPrompt, max_review_rounds: 2 },
        handleStatusUpdate,
      )

      // Mark all steps complete
      setSteps(prev => prev.map(s => ({ ...s, status: 'complete' as const })))

      toast({
        title: "Newsletter generated",
        description: "Your newsletter is ready to view",
      })

      onNewsletterGenerated(response.newsletter_id)
    } catch (err) {
      // Fallback to non-streaming on error
      try {
        const fullPrompt = buildPrompt()
        
        // Simulate step progress for non-streaming
        for (const step of initialSteps) {
          updateStep(step.id, 'active')
          await new Promise(r => setTimeout(r, 2000))
          updateStep(step.id, 'complete')
        }
        
        const response = await apiClient.generateNewsletter({
          prompt: fullPrompt,
          max_review_rounds: 2,
        })

        toast({
          title: "Newsletter generated",
          description: "Your newsletter is ready to view",
        })

        onNewsletterGenerated(response.newsletter_id)
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

      {/* Prompt Input */}
      <Card className="mb-8 border-border/50 shadow-sm">
        <CardContent className="p-0">
          <Textarea
            placeholder="Describe the briefing you'd like to generate — timeframe, regions, tone, or focus areas."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="min-h-32 resize-none border-0 bg-muted/30 px-6 py-5 text-base text-foreground placeholder:text-muted-foreground/60 focus-visible:ring-0"
            disabled={isGenerating}
          />
        </CardContent>
      </Card>

      {/* Advanced Settings */}
      <Collapsible open={isAdvancedOpen} onOpenChange={setIsAdvancedOpen} className="mb-10">
        <CollapsibleTrigger asChild>
          <button className="group flex items-center gap-2 text-sm text-muted-foreground/80 transition-colors hover:text-muted-foreground">
            <ChevronDown
              className={`h-4 w-4 transition-transform duration-200 ${isAdvancedOpen ? "rotate-180" : ""}`}
            />
            <span>Advanced Settings</span>
          </button>
        </CollapsibleTrigger>
        <p className="mt-1 text-xs text-muted-foreground/60">
          These will be inferred automatically, but can be fine-tuned.
        </p>
        <CollapsibleContent className="pt-6 space-y-8">
          {/* Time Window */}
          <div>
            <p className="mb-4 text-xs font-medium uppercase tracking-wide text-muted-foreground/70">
              Context
            </p>
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground/90">Time Window</Label>
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
        </CollapsibleContent>
      </Collapsible>

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

      {/* Primary CTA */}
      <div className="flex flex-col items-end gap-3">
        <Button
          onClick={handleGenerate}
          disabled={isGenerating || !prompt.trim()}
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
