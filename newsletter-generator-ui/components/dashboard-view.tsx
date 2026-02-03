"use client"

import { useState } from "react"
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Calendar, Building2, Cable, Radio, Plus, Loader2, RefreshCw, Trash2 } from "lucide-react"
import { apiClient, type NewsletterListItem } from "@/lib/api"
import { useToast } from "@/hooks/use-toast"

interface DashboardViewProps {
  onOpenNewsletter: (id: string) => void
  onStartGeneration: () => void
  newsletters: NewsletterListItem[]
  isLoading: boolean
  error: string | null
  onRefresh: () => void
}

const verticalIcons = {
  "Data Centers": Building2,
  "Connectivity & Fibre": Cable,
  "Towers & Wireless": Radio,
}

export function DashboardView({ 
  onOpenNewsletter, 
  onStartGeneration,
  newsletters,
  isLoading,
  error,
  onRefresh, 
}: DashboardViewProps) {
  const [sortBy, setSortBy] = useState("newest")
  const [filterRegion, setFilterRegion] = useState("all")
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const { toast } = useToast()

  const filteredNewsletters = newsletters
    .filter(n => filterRegion === "all" || n.regions.includes(filterRegion))
    .sort((a, b) => {
      if (sortBy === "newest") return new Date(b.date).getTime() - new Date(a.date).getTime()
      return new Date(a.date).getTime() - new Date(b.date).getTime()
    })

  const handleDeleteClick = (e: React.MouseEvent, id: string) => {
    e.stopPropagation() // Prevent opening the newsletter
    setDeleteConfirm(id)
  }

  const handleDeleteConfirm = async () => {
    if (!deleteConfirm) return
    
    setIsDeleting(true)
    try {
      await apiClient.deleteNewsletter(deleteConfirm)
      toast({
        title: "Newsletter deleted",
        description: "The newsletter has been permanently removed.",
      })
      onRefresh()
    } catch (err) {
      toast({
        title: "Delete failed",
        description: err instanceof Error ? err.message : "Failed to delete newsletter",
        variant: "destructive",
      })
    } finally {
      setIsDeleting(false)
      setDeleteConfirm(null)
    }
  }

  // Format voice profile for display, hiding default
  const formatVoice = (voice: string): string | null => {
    if (voice === "expert_operator") return null
    return voice.replace(/_/g, " ")
  }

  if (isLoading && newsletters.length === 0) {
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
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Newsletter Library
          </h1>
          <Button
            variant="ghost"
            size="icon"
            onClick={onRefresh}
            disabled={isLoading}
            className="h-8 w-8"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
        <p className="text-muted-foreground">
          Browse and edit your generated newsletters
        </p>
      </div>

      {error && (
        <Card className="mb-6 border-destructive/50 bg-destructive/10">
          <CardContent className="flex items-center justify-between py-4">
            <p className="text-sm text-destructive">{error}</p>
            <Button variant="outline" size="sm" onClick={onRefresh}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

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
            <SelectTrigger className="w-36 bg-card">
              <SelectValue placeholder="Region" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All regions</SelectItem>
              <SelectItem value="UK">UK</SelectItem>
              <SelectItem value="EU">EU</SelectItem>
              <SelectItem value="US">US</SelectItem>
              <SelectItem value="APAC">APAC</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button onClick={onStartGeneration} className="gap-2">
          <Plus className="h-4 w-4" />
          New Newsletter
        </Button>
      </div>

      {filteredNewsletters.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <p className="mb-4 text-muted-foreground">
              {newsletters.length === 0 
                ? "No newsletters generated yet. Create your first one!"
                : "No newsletters match your filter criteria."}
            </p>
            <Button onClick={onStartGeneration} variant="secondary" className="gap-2">
              <Plus className="h-4 w-4" />
              Generate Newsletter
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredNewsletters.map((newsletter) => {
            const displayVoice = formatVoice(newsletter.voiceProfile)
            
            return (
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
                    <div className="flex items-center gap-2">
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
                        {displayVoice && (
                          <Badge
                            variant="outline"
                            className="px-2 py-0.5 text-xs font-normal text-muted-foreground border-muted"
                          >
                            {displayVoice}
                          </Badge>
                        )}
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                        onClick={(e) => handleDeleteClick(e, newsletter.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Newsletter?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. This will permanently delete the newsletter
              and all associated research data and artifacts.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
