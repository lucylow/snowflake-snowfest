"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, Atom } from "lucide-react"

interface MoleculeViewer2DProps {
  pdbData?: string
  jobId?: string
  poseId?: number
  title?: string
  description?: string
}

export function MoleculeViewer2D({ pdbData, jobId, poseId = 0, title, description }: MoleculeViewer2DProps) {
  // Parse PDB data to extract basic info
  const parseAtomCount = (pdbString: string) => {
    if (!pdbString) return 0
    const atomLines = pdbString.split("\n").filter((line) => line.startsWith("ATOM"))
    return atomLines.length
  }

  const parseResidues = (pdbString: string) => {
    if (!pdbString) return []
    const atomLines = pdbString.split("\n").filter((line) => line.startsWith("ATOM"))
    const residues = new Set<string>()
    atomLines.forEach((line) => {
      const residue = line.substring(17, 20).trim()
      if (residue) residues.add(residue)
    })
    return Array.from(residues)
  }

  const atomCount = parseAtomCount(pdbData || "")
  const residues = parseResidues(pdbData || "")

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title || "Molecular Structure"}</CardTitle>
        <CardDescription>{description || "2D representation of protein-ligand structure"}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="w-full h-[500px] border rounded-lg overflow-hidden bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 p-8">
          <div className="flex flex-col items-center justify-center h-full space-y-8">
            <div className="relative w-full max-w-md aspect-square">
              <svg viewBox="0 0 400 400" className="w-full h-full">
                {/* Protein backbone representation */}
                <circle cx="200" cy="200" r="120" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                <circle cx="200" cy="200" r="100" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.3" />
                <circle cx="200" cy="200" r="80" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.3" />

                {/* Ligand binding site representation */}
                <circle cx="200" cy="200" r="40" fill="hsl(var(--primary))" opacity="0.2" />
                <circle cx="200" cy="200" r="40" fill="none" stroke="hsl(var(--primary))" strokeWidth="3" />

                {/* Atom nodes */}
                {[...Array(12)].map((_, i) => {
                  const angle = (i * Math.PI * 2) / 12
                  const x = 200 + Math.cos(angle) * 80
                  const y = 200 + Math.sin(angle) * 80
                  return (
                    <g key={i}>
                      <line x1="200" y1="200" x2={x} y2={y} stroke="currentColor" strokeWidth="1.5" opacity="0.4" />
                      <circle cx={x} cy={y} r="6" fill="hsl(var(--primary))" stroke="white" strokeWidth="2" />
                    </g>
                  )
                })}

                {/* Central binding site */}
                <circle cx="200" cy="200" r="12" fill="hsl(var(--destructive))" stroke="white" strokeWidth="2" />
                <Atom className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-5 h-5 text-white" />
              </svg>
            </div>

            {/* Structure information */}
            <div className="grid grid-cols-2 gap-6 w-full max-w-md">
              <div className="text-center p-4 bg-white dark:bg-slate-800 rounded-lg shadow-sm">
                <Activity className="w-6 h-6 mx-auto mb-2 text-primary" />
                <p className="text-2xl font-bold">{atomCount}</p>
                <p className="text-sm text-muted-foreground">Total Atoms</p>
              </div>
              <div className="text-center p-4 bg-white dark:bg-slate-800 rounded-lg shadow-sm">
                <Atom className="w-6 h-6 mx-auto mb-2 text-primary" />
                <p className="text-2xl font-bold">{residues.length}</p>
                <p className="text-sm text-muted-foreground">Residues</p>
              </div>
            </div>

            {/* Residue list */}
            {residues.length > 0 && (
              <div className="flex flex-wrap gap-2 justify-center max-w-md">
                {residues.slice(0, 10).map((residue, idx) => (
                  <Badge key={idx} variant="secondary" className="text-xs">
                    {residue}
                  </Badge>
                ))}
                {residues.length > 10 && (
                  <Badge variant="outline" className="text-xs">
                    +{residues.length - 10} more
                  </Badge>
                )}
              </div>
            )}

            <p className="text-sm text-muted-foreground text-center max-w-md">
              This is a simplified 2D representation. For full interactive 3D visualization, ensure the 3Dmol library is
              loaded correctly.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
