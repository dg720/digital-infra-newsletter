"use client"

import React from "react"

import { useState, useRef, useEffect, useCallback } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { 
  Building2, 
  Cable, 
  Radio, 
  Calendar, 
  Send,
  Loader2,
  ChevronUp,
  ChevronDown,
  User,
  Bot,
  AlertCircle,
  CheckCircle
} from "lucide-react"
import { fetchNewsletterDetail, apiClient } from "@/lib/api"
import type { NewsletterDetail, SectionForUI } from "@/lib/api"

interface NewsletterReadingViewProps {
  newsletterId: string
  onBack: () => void
}

type SectionKey = "dataCenters" | "connectivity" | "towers"

interface ChatMessage {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
  status?: 'pending' | 'success' | 'error'
}

const sectionConfig: Record<SectionKey, { title: string; icon: typeof Building2; backendId: string }> = {
  dataCenters: { title: "Data Centers", icon: Building2, backendId: "data_centers" },
  connectivity: { title: "Connectivity & Fibre", icon: Cable, backendId: "connectivity_fibre" },
  towers: { title: "Towers & Wireless", icon: Radio, backendId: "towers_wireless" },
}

const statusMessages = [
  "Gathering new sources...",
  "Researching updates...",
  "Reviewing changes...",
  "Editing section...",
  "Saving changes...",
]

export function NewsletterReadingView({ newsletterId, onBack }: NewsletterReadingViewProps) {
  const [newsletter, setNewsletter] = useState<NewsletterDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [editPrompt, setEditPrompt] = useState("")
  const [isChatExpanded, setIsChatExpanded] = useState(true)
  const [isUpdating, setIsUpdating] = useState(false)
  const [updatingSection, setUpdatingSection] = useState<SectionKey | null>(null)
  const [statusMessage, setStatusMessage] = useState("")
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "I can help you refine this newsletter. Try something like \"Tighten the towers section and add more European context\" or \"Make the data centres section more analytical.\"",
      timestamp: new Date(),
    },
  ])
  const [highlightedSection, setHighlightedSection] = useState<SectionKey | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const loadNewsletter = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)
    try {
      const data = await fetchNewsletterDetail(newsletterId)
      setNewsletter(data)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load newsletter')
    } finally {
      setIsLoading(false)
    }
  }, [newsletterId])

  useEffect(() => {
    loadNewsletter()
  }, [loadNewsletter])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chatMessages])

  useEffect(() => {
    if (highlightedSection) {
      const timer = setTimeout(() => setHighlightedSection(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [highlightedSection])

  const detectAffectedSection = (prompt: string): SectionKey => {
    const lower = prompt.toLowerCase()
    if (lower.includes("data cent") || lower.includes("dc ") || lower.includes("colocation") || lower.includes("hyperscale")) return "dataCenters"
    if (lower.includes("connect") || lower.includes("fibre") || lower.includes("fiber") || lower.includes("submarine") || lower.includes("network")) return "connectivity"
    if (lower.includes("tower") || lower.includes("wireless") || lower.includes("5g") || lower.includes("mobile") || lower.includes("cell")) return "towers"
    return "dataCenters" // Default to first section
  }

  const handleSubmitEdit = async () => {
    if (!editPrompt.trim() || !newsletter) return

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: editPrompt,
      timestamp: new Date(),
    }
    setChatMessages((prev) => [...prev, userMessage])

    const affectedSection = detectAffectedSection(editPrompt)
    const backendSectionId = sectionConfig[affectedSection].backendId
    setUpdatingSection(affectedSection)
    setIsUpdating(true)
    setEditPrompt("")

    // Show status updates
    let statusIndex = 0
    const statusInterval = setInterval(() => {
      if (statusIndex < statusMessages.length) {
        setStatusMessage(statusMessages[statusIndex])
        statusIndex++
      }
    }, 1500)

    try {
      // Call the real section update API
      await apiClient.updateSection(newsletterId, {
        section_id: backendSectionId,
        instruction: userMessage.content,
      })

      clearInterval(statusInterval)
      setStatusMessage("Complete!")

      // Reload the newsletter to get updated content
      await loadNewsletter()

      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `✓ Updated the ${sectionConfig[affectedSection].title} section based on your request. The changes have been applied and highlighted above.`,
        timestamp: new Date(),
        status: 'success',
      }
      setChatMessages((prev) => [...prev, assistantMessage])

      setHighlightedSection(affectedSection)
    } catch (err) {
      clearInterval(statusInterval)
      
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `I wasn't able to update the section: ${errorMessage}`,
        timestamp: new Date(),
        status: 'error',
      }
      setChatMessages((prev) => [...prev, assistantMessage])
    } finally {
      setIsUpdating(false)
      setUpdatingSection(null)
      setStatusMessage("")
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmitEdit()
    }
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading newsletter...</p>
        </div>
      </div>
    )
  }

  if (loadError || !newsletter) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-center">
          <AlertCircle className="h-8 w-8 text-destructive" />
          <p className="text-sm text-destructive">{loadError || 'Newsletter not found'}</p>
          <Button variant="outline" onClick={onBack}>
            Back to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  const renderSection = (key: SectionKey, section: SectionForUI) => {
    if (!section.bigPicture && section.bullets.length === 0) return null

    const config = sectionConfig[key]
    const Icon = config.icon
    const isUpdatingThis = updatingSection === key
    const isHighlighted = highlightedSection === key

    return (
      <section
        key={key}
        className={`relative ${isHighlighted ? "rounded-lg ring-2 ring-green-500/40 ring-offset-4 ring-offset-background" : ""}`}
      >
        {/* Status badge - above blur layer */}
        {isUpdatingThis && (
          <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none">
            <div className="flex items-center gap-2 rounded-full bg-card px-4 py-2 shadow-lg border">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="text-sm font-medium text-foreground">
                {statusMessage || "Updating section..."}
              </span>
            </div>
          </div>
        )}
        
        {/* Section content - gets blurred when updating */}
        <div className={`transition-all duration-500 ${isUpdatingThis ? "opacity-40 blur-[2px]" : ""}`}>

        <div className="mb-4 flex items-center gap-3">
          <div className={`flex h-9 w-9 items-center justify-center rounded-lg transition-colors ${
            isHighlighted ? "bg-green-500/20" : "bg-primary/10"
          }`}>
            {isHighlighted ? (
              <CheckCircle className="h-5 w-5 text-green-500" />
            ) : (
              <Icon className="h-5 w-5 text-primary" />
            )}
          </div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            {config.title}
            {isHighlighted && (
              <span className="ml-2 text-sm font-normal text-green-500">Updated</span>
            )}
          </h2>
        </div>

        {section.bigPicture && (() => {
          // Extract citation numbers and make them clickable
          const citationMatch = section.bigPicture.match(/\[\d+\]/g)
          const cleanText = section.bigPicture.replace(/\s*\[\d+\]+/g, '')
          
          return (
            <p className="mb-5 text-base leading-relaxed text-foreground/90">
              {cleanText}
              {citationMatch && citationMatch.map((cite, i) => {
                const num = parseInt(cite.replace(/[\[\]]/g, ''), 10)
                const evidence = section.evidence[num - 1]
                if (evidence?.url) {
                  return (
                    <a 
                      key={i}
                      href={evidence.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="ml-0.5 text-xs font-medium text-primary hover:underline"
                    >
                      [{num}]
                    </a>
                  )
                }
                return (
                  <sup key={i} className="ml-0.5 text-xs font-medium text-muted-foreground">
                    [{num}]
                  </sup>
                )
              })}
            </p>
          )
        })()}

        {section.bullets.length > 0 && (
          <ul className="space-y-3">
            {section.bullets.map((bullet, index) => {
              // Extract citation numbers from text and match to evidence URLs
              const citationMatch = bullet.text.match(/\[\d+\]/g)
              const cleanText = bullet.text.replace(/\s*\[\d+\]+/g, '')
              
              return (
                <li key={index} className="flex gap-3 text-sm leading-relaxed text-foreground/80">
                  <span className="mt-2 h-1 w-1 flex-shrink-0 rounded-full bg-muted-foreground/50" />
                  <span>
                    {cleanText}
                    {citationMatch && citationMatch.map((cite, i) => {
                      const num = parseInt(cite.replace(/[\[\]]/g, ''), 10)
                      const evidence = section.evidence[num - 1] // Citations are 1-indexed
                      if (evidence?.url) {
                        return (
                          <a 
                            key={i}
                            href={evidence.url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="ml-0.5 text-[10px] font-medium text-primary hover:underline"
                          >
                            [{num}]
                          </a>
                        )
                      }
                      return (
                        <sup key={i} className="ml-0.5 text-[10px] font-medium text-muted-foreground">
                          [{num}]
                        </sup>
                      )
                    })}
                  </span>
                </li>
              )
            })}
          </ul>
        )}

        {section.evidence.length > 0 && (
          <div className="mt-4 pt-3 border-t border-border">
            <p className="text-xs font-medium text-muted-foreground mb-2">Sources</p>
            <div className="flex flex-col gap-1">
              {section.evidence.map((e, idx) => (
                <div key={e.id} className="text-xs text-muted-foreground">
                  <span className="font-medium">[{idx + 1}]</span>{' '}
                  {e.url ? (
                    <a 
                      href={e.url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-primary hover:underline"
                    >
                      {e.title || e.source}
                    </a>
                  ) : (
                    <span>{e.title || e.source}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        </div>
      </section>
    )
  }

  return (
    <div className="pb-48">
      {/* Newsletter Header */}
      <div className="border-b border-border bg-card/50">
        <div className="container mx-auto max-w-3xl px-4 py-10">
          <h1 className="mb-4 text-balance text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
            {newsletter.title}
          </h1>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <Calendar className="h-4 w-4" />
              {new Date(newsletter.timeWindow.start).toLocaleDateString("en-GB", {
                day: "numeric",
                month: "long",
              })}
              {" — "}
              {new Date(newsletter.timeWindow.end).toLocaleDateString("en-GB", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </span>
            {newsletter.voiceProfile !== 'expert_operator' && (
              <>
                <span className="text-border">|</span>
                <span className="capitalize">{newsletter.voiceProfile.replace(/_/g, ' ')} voice</span>
              </>
            )}
            <span className="text-border">|</span>
            <span>{newsletter.regions.join(", ")}</span>
          </div>
        </div>
      </div>

      {/* Newsletter Content */}
      <article className="container mx-auto max-w-3xl px-4 py-10">
        <div className="space-y-12">
          {(Object.keys(newsletter.sections) as SectionKey[]).map((key) =>
            renderSection(key, newsletter.sections[key])
          )}
        </div>
      </article>

      {/* Edit Chat Panel */}
      <div className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 shadow-lg backdrop-blur-sm">
        <div className="container mx-auto max-w-3xl px-4">
          {/* Status Ribbon */}
          {isUpdating && statusMessage && (
            <div className="flex items-center gap-2 border-b border-border py-2 text-sm text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
              <span>{statusMessage}</span>
            </div>
          )}

          {/* Chat Toggle */}
          <button
            onClick={() => setIsChatExpanded(!isChatExpanded)}
            className="flex w-full items-center justify-between py-3 text-sm font-medium text-foreground hover:text-primary"
          >
            <span>Edit this newsletter</span>
            {isChatExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronUp className="h-4 w-4" />
            )}
          </button>

          {/* Chat Messages */}
          {isChatExpanded && (
            <div className="max-h-48 space-y-3 overflow-y-auto border-t border-border py-3">
              {chatMessages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-2.5 ${message.role === "user" ? "justify-end" : ""}`}
                >
                  {message.role === "assistant" && (
                    <div className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full ${
                      message.status === 'error' ? 'bg-destructive/10' :
                      message.status === 'success' ? 'bg-green-500/10' :
                      'bg-primary/10'
                    }`}>
                      {message.status === 'error' ? (
                        <AlertCircle className="h-4 w-4 text-destructive" />
                      ) : message.status === 'success' ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <Bot className="h-4 w-4 text-primary" />
                      )}
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                      message.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : message.status === 'error'
                        ? "bg-destructive/10 text-destructive"
                        : message.status === 'success'
                        ? "bg-green-500/10 text-foreground"
                        : "bg-muted text-foreground"
                    }`}
                  >
                    {message.content}
                  </div>
                  {message.role === "user" && (
                    <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-muted">
                      <User className="h-4 w-4 text-muted-foreground" />
                    </div>
                  )}
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
          )}

          {/* Input Area */}
          <div className="flex items-end gap-2 border-t border-border py-3">
            <Textarea
              ref={textareaRef}
              value={editPrompt}
              onChange={(e) => setEditPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe changes... e.g. 'Add more detail about European expansion in data centers'"
              className="max-h-24 min-h-10 flex-1 resize-none border-0 bg-transparent p-0 text-sm placeholder:text-muted-foreground focus-visible:ring-0"
              disabled={isUpdating}
            />
            <Button
              size="sm"
              onClick={handleSubmitEdit}
              disabled={!editPrompt.trim() || isUpdating}
              className="flex-shrink-0"
            >
              {isUpdating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
