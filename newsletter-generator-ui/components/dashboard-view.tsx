"use client"

import { useState, useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Calendar, Building2, Cable, Radio, Plus, Loader2 } from "lucide-react"
import { fetchNewsletterList, type NewsletterListItem } from "@/lib/api"

interface DashboardViewProps {
  onOpenNewsletter: (id: string) => void
  onStartGeneration: () => void
}

const verticalIcons = {
  "Data Centers": Building2,
  "Connectivity & Fibre": Cable,
  "Towers & Wireless": Radio,
}

export function DashboardView({ onOpenNewsletter, onStartGeneration }: DashboardViewProps) {
  const [sortBy, setSortBy] = useState("newest")
  const [filterRegion, setFilterRegion] = useState("all")
  const [newsletters, setNewsletters] = useState<NewsletterListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadNewsletters()
  }, [])

  const loadNewsletters = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await fetchNewsletterList()
      setNewsletters(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load newsletters')
    } finally {
      setIsLoading(false)
    }
  }

  const filteredNewsletters = newsletters
    .filter(n => filterRegion === "all" || n.regions.includes(filterRegion))
    .sort((a, b) => {
      if (sortBy === "newest") return new Date(b.date).getTime() - new Date(a.date).getTime()
      return new Date(a.date).getTime() - new Date(b.date).getTime()
    })

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-4xl px-4 py-8">
        <div className="flex min-h-[40vh] items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Loading newsletters...</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-4xl px-4 py-8">
      <div className="mb-8 space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Newsletter Library
        </h1>
        <p className="text-muted-foreground">
          Browse and edit your generated newsletters
        </p>
      </div>

      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-36 bg-card">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="newest">Newest first</SelectItem>
              <SelectItem value="oldest">Oldest first</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filterRegion} onValueChange={setFilterRegion}>
            <SelectTrigger className="w-32 bg-card">
              <SelectValue placeholder="Region" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All regions</SelectItem>
              <SelectItem value="UK">UK</SelectItem>
              <SelectItem value="EU">EU</SelectItem>
              <SelectItem value="US">US</SelectItem>
              <SelectItem value="APAC">APAC</SelectItem>
              <SelectItem value="Global">Global</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="ghost"
            size="sm"
            onClick={loadNewsletters}
            className="gap-2"
          >
            Refresh
          </Button>
        </div>
        <Button
          variant="outline"
          onClick={onStartGeneration}
          className="gap-2 sm:hidden bg-transparent"
        >
          <Plus className="h-4 w-4" />
          New Newsletter
        </Button>
      </div>

      {error && (
        <Card className="mb-6 border-destructive/50 bg-destructive/10">
          <CardContent className="py-4 text-center">
            <p className="text-sm text-destructive">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={loadNewsletters}
              className="mt-2"
            >
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {filteredNewsletters.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <Calendar className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="mb-1 font-medium text-foreground">No newsletters yet</h3>
            <p className="mb-4 text-sm text-muted-foreground">
              Generate your first newsletter to get started
            </p>
            <Button onClick={onStartGeneration} className="gap-2">
              <Plus className="h-4 w-4" />
              Create Newsletter
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredNewsletters.map((newsletter) => (
            <Card
              key={newsletter.id}
              className="group cursor-pointer border-border transition-all hover:border-primary/30 hover:shadow-md"
              onClick={() => onOpenNewsletter(newsletter.id)}
            >
              <CardContent className="p-5">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0 flex-1 space-y-2">
                    <h3 className="font-medium leading-snug text-foreground group-hover:text-primary">
                      {newsletter.title}
                    </h3>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <Calendar className="h-3.5 w-3.5" />
                        {new Date(newsletter.timeWindow.start).toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "short",
                        })}
                        {" — "}
                        {new Date(newsletter.timeWindow.end).toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {newsletter.regions.map((region) => (
                      <Badge
                        key={region}
                        variant="outline"
                        className="px-2 py-0.5 text-xs font-normal text-primary border-primary/40"
                      >
                        {region}
                      </Badge>
                    ))}
                    {newsletter.verticals.map((vertical) => {
                      const Icon = verticalIcons[vertical as keyof typeof verticalIcons]
                      return (
                        <Badge
                          key={vertical}
                          variant="secondary"
                          className="gap-1 bg-muted/80 px-2 py-0.5 text-xs font-normal text-muted-foreground"
                        >
                          {Icon && <Icon className="h-3 w-3" />}
                          <span className="hidden md:inline">{vertical}</span>
                        </Badge>
                      )
                    })}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
