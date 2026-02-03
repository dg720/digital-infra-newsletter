"use client"

import { useRef, useEffect, useState } from "react"
import { ChevronDown, ChevronRight, Terminal, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export interface DebugEvent {
  id: string
  timestamp: Date
  category: 'node' | 'tool' | 'llm' | 'llm_stream' | 'unknown'
  content: string
  metadata?: Record<string, unknown>
}

interface DebugTerminalProps {
  events: DebugEvent[]
  onClear?: () => void
  isGenerating?: boolean
}

export function DebugTerminal({ events, onClear, isGenerating = false }: DebugTerminalProps) {
  const [isOpen, setIsOpen] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events, autoScroll])

  // Handle scroll to detect if user scrolled up
  const handleScroll = () => {
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
      const isAtBottom = scrollHeight - scrollTop - clientHeight < 50
      setAutoScroll(isAtBottom)
    }
  }

  const getCategoryColor = (category: DebugEvent['category']) => {
    switch (category) {
      case 'node':
        return 'text-blue-400'
      case 'tool':
        return 'text-yellow-400'
      case 'llm':
        return 'text-green-400'
      case 'llm_stream':
        return 'text-green-300/70'
      default:
        return 'text-gray-400'
    }
  }

  const getCategoryBadge = (category: DebugEvent['category']) => {
    switch (category) {
      case 'node':
        return 'NODE'
      case 'tool':
        return 'TOOL'
      case 'llm':
        return 'LLM'
      case 'llm_stream':
        return ''
      default:
        return 'INFO'
    }
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    })
  }

  return (
    <div className="border border-border rounded-lg bg-card overflow-hidden">
      {/* Header - always visible */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-muted/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Debug Terminal</span>
          {events.length > 0 && (
            <span className="text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              {events.length} events
            </span>
          )}
          {isGenerating && (
            <span className="flex items-center gap-1">
              <span className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-xs text-green-500">Live</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isOpen && onClear && events.length > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={(e) => {
                e.stopPropagation()
                onClear()
              }}
              className="h-6 px-2 text-xs"
            >
              <Trash2 className="h-3 w-3 mr-1" />
              Clear
            </Button>
          )}
          {isOpen ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Terminal content - collapsible */}
      {isOpen && (
        <div 
          ref={scrollRef}
          onScroll={handleScroll}
          className="bg-zinc-950 text-zinc-100 font-mono text-xs max-h-80 overflow-y-auto p-3 border-t border-border"
        >
          {events.length === 0 ? (
            <div className="text-zinc-500 text-center py-8">
              No debug events yet. Start generating to see agent activity.
            </div>
          ) : (
            <div className="space-y-1">
              {events.map((event) => (
                <div key={event.id} className="flex gap-2 leading-relaxed">
                  <span className="text-zinc-500 flex-shrink-0">
                    {formatTime(event.timestamp)}
                  </span>
                  {event.category !== 'llm_stream' && (
                    <span className={cn(
                      "flex-shrink-0 font-semibold w-12",
                      getCategoryColor(event.category)
                    )}>
                      {getCategoryBadge(event.category)}
                    </span>
                  )}
                  <span className={cn(
                    "flex-1",
                    event.category === 'llm_stream' ? 'text-green-300/70 pl-14' : 'text-zinc-200'
                  )}>
                    {event.content}
                  </span>
                </div>
              ))}
              {isGenerating && (
                <div className="flex gap-2 items-center text-zinc-500">
                  <span className="inline-block animate-pulse">▌</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
