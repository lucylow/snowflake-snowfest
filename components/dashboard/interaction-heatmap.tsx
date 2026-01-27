"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface InteractionData {
  residue: string
  type: string
  distance: number
  energy: number
}

export function InteractionHeatmap() {
  const interactions: InteractionData[] = [
    { residue: "Ser530", type: "H-Bond", distance: 2.1, energy: -3.2 },
    { residue: "Tyr385", type: "π-Stacking", distance: 3.8, energy: -2.8 },
    { residue: "Val523", type: "Hydrophobic", distance: 3.5, energy: -1.9 },
    { residue: "Ala527", type: "Hydrophobic", distance: 3.9, energy: -1.5 },
    { residue: "Arg120", type: "Ionic", distance: 2.8, energy: -4.1 },
    { residue: "Phe518", type: "π-π", distance: 4.2, energy: -2.3 },
  ]

  const getEnergyColor = (energy: number) => {
    if (energy <= -3) return "bg-green-500"
    if (energy <= -2) return "bg-blue-500"
    if (energy <= -1) return "bg-yellow-500"
    return "bg-orange-500"
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Key Molecular Interactions</CardTitle>
        <CardDescription>Protein-ligand binding interactions with energy contributions</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {interactions.map((interaction, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${getEnergyColor(interaction.energy)}`} />
                <div>
                  <p className="font-medium">{interaction.residue}</p>
                  <p className="text-sm text-muted-foreground">{interaction.type}</p>
                </div>
              </div>
              <div className="text-right space-y-1">
                <Badge variant="outline" className="text-xs">
                  {interaction.distance.toFixed(1)} Å
                </Badge>
                <p className="text-sm font-semibold">{interaction.energy.toFixed(1)} kcal/mol</p>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 pt-4 border-t">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <span>Strong (&lt; -3)</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-blue-500" />
              <span>Medium (-2 to -3)</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-yellow-500" />
              <span>Weak (-1 to -2)</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
