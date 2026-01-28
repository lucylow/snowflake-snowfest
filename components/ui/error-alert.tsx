"use client"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle, XCircle, WifiOff, RefreshCw, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useState } from "react"

interface ErrorAlertProps {
  title?: string
  message: string
  onRetry?: () => void
  onDismiss?: () => void
  variant?: "default" | "destructive"
  dismissible?: boolean
}

export function ErrorAlert({ 
  title = "Error", 
  message, 
  onRetry, 
  onDismiss,
  variant = "destructive",
  dismissible = false 
}: ErrorAlertProps) {
  const [dismissed, setDismissed] = useState(false)

  const getIcon = () => {
    if (message.includes("network") || message.includes("connect")) {
      return <WifiOff className="h-4 w-4" />
    }
    if (variant === "destructive") {
      return <XCircle className="h-4 w-4" />
    }
    return <AlertCircle className="h-4 w-4" />
  }

  const handleDismiss = () => {
    setDismissed(true)
    onDismiss?.()
  }

  if (dismissed) return null

  return (
    <Alert variant={variant} className="relative">
      {getIcon()}
      <AlertTitle className="pr-8">{title}</AlertTitle>
      <AlertDescription className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pr-8">
        <span className="flex-1">{message}</span>
        <div className="flex items-center gap-2">
          {onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry} className="gap-2">
              <RefreshCw className="h-3 w-3" />
              Retry
            </Button>
          )}
        </div>
      </AlertDescription>
      {dismissible && (
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-2 right-2 h-6 w-6 p-0"
          onClick={handleDismiss}
          aria-label="Dismiss"
        >
          <X className="h-3 w-3" />
        </Button>
      )}
    </Alert>
  )
}
