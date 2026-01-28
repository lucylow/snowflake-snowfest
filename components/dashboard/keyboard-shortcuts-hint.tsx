"use client"

import { useState, useEffect } from "react"
import { Badge } from "@/components/ui/badge"
import { Keyboard, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export function KeyboardShortcutsHint() {
  const [isVisible, setIsVisible] = useState(false)
  const [isDismissed, setIsDismissed] = useState(false)

  useEffect(() => {
    // Show hint after 3 seconds if not dismissed
    const timer = setTimeout(() => {
      const dismissed = localStorage.getItem("keyboard-shortcuts-dismissed")
      if (!dismissed) {
        setIsVisible(true)
      }
    }, 3000)

    return () => clearTimeout(timer)
  }, [])

  const handleDismiss = () => {
    setIsDismissed(true)
    setIsVisible(false)
    localStorage.setItem("keyboard-shortcuts-dismissed", "true")
  }

  if (isDismissed || !isVisible) return null

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="fixed bottom-4 right-4 z-50 animate-in slide-in-from-bottom-4">
            <Badge
              variant="secondary"
              className="flex items-center gap-2 px-3 py-2 shadow-lg cursor-pointer hover:bg-muted/80 transition-colors"
            >
              <Keyboard className="h-3 w-3" />
              <span className="text-xs">
                Press <kbd className="px-1 py-0.5 text-xs font-semibold bg-background border rounded">Ctrl+N</kbd> for new job
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-4 w-4 p-0 ml-1"
                onClick={(e) => {
                  e.stopPropagation()
                  handleDismiss()
                }}
              >
                <X className="h-3 w-3" />
              </Button>
            </Badge>
          </div>
        </TooltipTrigger>
        <TooltipContent side="left" className="max-w-xs">
          <div className="space-y-2 text-xs">
            <p className="font-semibold mb-2">Keyboard Shortcuts:</p>
            <div className="space-y-1">
              <div className="flex items-center justify-between gap-4">
                <span>New Job</span>
                <kbd className="px-1.5 py-0.5 text-xs font-semibold bg-muted border rounded">Ctrl+N</kbd>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span>Focus Search</span>
                <kbd className="px-1.5 py-0.5 text-xs font-semibold bg-muted border rounded">/</kbd>
              </div>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
