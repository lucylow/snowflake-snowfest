"use client"

import { useEffect, useRef, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Loader2, Download, RotateCcw, ZoomIn, ZoomOut, AlertCircle } from "lucide-react"
import Script from "next/script"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { MoleculeViewer2D } from "./molecule-viewer-2d"

interface MoleculeViewerProps {
  pdbData?: string
  jobId?: string
  poseId?: number
  title?: string
  description?: string
}

declare global {
  interface Window {
    $3Dmol: any
  }
}

export function MoleculeViewer({ pdbData, jobId, poseId = 0, title, description }: MoleculeViewerProps) {
  const viewerRef = useRef<HTMLDivElement>(null)
  const viewerInstanceRef = useRef<any>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [scriptLoaded, setScriptLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [use2DFallback, setUse2DFallback] = useState(false)
  const retryCountRef = useRef(0)

  useEffect(() => {
    setUse2DFallback(false)
    setError(null)
    setIsLoading(true)
    retryCountRef.current = 0
  }, [pdbData, poseId])

  useEffect(() => {
    if (!pdbData) {
      setError("No molecular structure data available")
      setIsLoading(false)
      setUse2DFallback(true)
      return
    }

    if (!scriptLoaded || !viewerRef.current) {
      return
    }

    if (!window.$3Dmol) {
      if (retryCountRef.current < 3) {
        retryCountRef.current++
        setTimeout(() => setScriptLoaded(true), 1000)
        return
      } else {
        setError("3D visualization library failed to load")
        setIsLoading(false)
        setUse2DFallback(true)
        return
      }
    }

    try {
      setError(null)

      if (viewerInstanceRef.current) {
        try {
          viewerInstanceRef.current.clear()
        } catch (e) {
          console.error("[v0] Error clearing viewer:", e)
        }
      }

      const viewer = window.$3Dmol.createViewer(viewerRef.current, {
        backgroundColor: "white",
      })
      viewerInstanceRef.current = viewer

      viewer.addModel(pdbData, "pdb")
      viewer.setStyle({}, { cartoon: { color: "spectrum" } })
      viewer.addSurface(window.$3Dmol.SurfaceType.VDW, { opacity: 0.7, color: "white" })
      viewer.zoomTo()
      viewer.render()

      setIsLoading(false)
    } catch (error) {
      console.error("[v0] 3Dmol viewer error:", error)
      setError("Failed to render 3D structure")
      setIsLoading(false)
      setUse2DFallback(true)
    }

    return () => {
      if (viewerInstanceRef.current) {
        try {
          viewerInstanceRef.current.clear()
        } catch (error) {
          console.error("[v0] Error clearing viewer:", error)
        }
      }
    }
  }, [pdbData, scriptLoaded])

  const handleReset = () => {
    if (viewerInstanceRef.current) {
      try {
        viewerInstanceRef.current.zoomTo()
        viewerInstanceRef.current.render()
      } catch (error) {
        console.error("[v0] Reset error:", error)
      }
    }
  }

  const handleZoomIn = () => {
    if (viewerInstanceRef.current) {
      try {
        viewerInstanceRef.current.zoom(1.2)
        viewerInstanceRef.current.render()
      } catch (error) {
        console.error("[v0] Zoom in error:", error)
      }
    }
  }

  const handleZoomOut = () => {
    if (viewerInstanceRef.current) {
      try {
        viewerInstanceRef.current.zoom(0.8)
        viewerInstanceRef.current.render()
      } catch (error) {
        console.error("[v0] Zoom out error:", error)
      }
    }
  }

  const handleDownload = () => {
    if (pdbData) {
      try {
        const blob = new Blob([pdbData], { type: "text/plain" })
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `structure_${jobId || "unknown"}_pose_${poseId}.pdb`
        a.click()
        URL.revokeObjectURL(url)
      } catch (error) {
        console.error("[v0] Download error:", error)
      }
    }
  }

  if (use2DFallback) {
    return (
      <div className="space-y-4">
        {error && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>3D Visualization Unavailable</AlertTitle>
            <AlertDescription>
              {error}. Showing 2D representation instead. You can still download the PDB file below.
            </AlertDescription>
          </Alert>
        )}
        <MoleculeViewer2D pdbData={pdbData} jobId={jobId} poseId={poseId} title={title} description={description} />
        {pdbData && (
          <div className="flex justify-center">
            <Button onClick={handleDownload} variant="outline" className="gap-2 bg-transparent">
              <Download className="w-4 h-4" />
              Download PDB File
            </Button>
          </div>
        )}
      </div>
    )
  }

  return (
    <>
      <Script
        src="https://3Dmol.csb.pitt.edu/build/3Dmol-min.js"
        strategy="lazyOnload"
        onLoad={() => {
          setScriptLoaded(true)
        }}
        onError={() => {
          console.error("[v0] Failed to load 3Dmol script")
          setError("Failed to load 3D visualization library")
          setIsLoading(false)
          setUse2DFallback(true)
        }}
      />
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{title || "3D Molecular Structure"}</CardTitle>
              <CardDescription>{description || "Interactive protein-ligand visualization"}</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="icon" onClick={handleZoomIn} disabled={isLoading || !!error}>
                <ZoomIn className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="icon" onClick={handleZoomOut} disabled={isLoading || !!error}>
                <ZoomOut className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="icon" onClick={handleReset} disabled={isLoading || !!error}>
                <RotateCcw className="w-4 h-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={handleDownload}
                disabled={isLoading || !pdbData || !!error}
              >
                <Download className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="relative w-full h-[500px] border rounded-lg overflow-hidden bg-white">
            {isLoading && !error && (
              <div className="absolute inset-0 flex items-center justify-center bg-background/50 z-10">
                <div className="text-center">
                  <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-2" />
                  <p className="text-sm text-muted-foreground">Loading 3D visualization...</p>
                </div>
              </div>
            )}
            <div ref={viewerRef} className="w-full h-full" />
          </div>
        </CardContent>
      </Card>
    </>
  )
}
