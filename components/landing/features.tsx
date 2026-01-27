import { Card, CardContent } from "@/components/ui/card"
import { Cpu, Brain, Microscope, Activity } from "lucide-react"

const features = [
  {
    icon: Cpu,
    title: "GPU-Accelerated Docking",
    description:
      "Lightning-fast molecular docking with AutoDock Vina. Screen thousands of compounds against drug targets in minutes, not days.",
  },
  {
    icon: Brain,
    title: "AlphaFold Integration",
    description:
      "Predict 3D protein structures from amino acid sequences using AlphaFold2. No experimental structure required.",
  },
  {
    icon: Microscope,
    title: "AI Drug Screening",
    description:
      "ML-powered analysis of binding affinity, drug-likeness, ADMET properties, and toxicity predictions for every candidate.",
  },
  {
    icon: Activity,
    title: "Clinical Insights",
    description:
      "Generate stakeholder-specific reports for researchers, clinicians, investors, and regulators with AI-powered recommendations.",
  },
]

export function Features() {
  return (
    <section id="features" className="bg-muted/30">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 sm:py-32 md:py-40">
        <div className="text-center mb-16 sm:mb-20">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl mb-4 sm:mb-6 text-balance">
            Complete AI Platform for Drug Discovery
          </h2>
          <p className="text-base text-muted-foreground sm:text-lg md:text-xl max-w-2xl mx-auto text-pretty leading-relaxed">
            From protein sequence to drug candidate analysis—powered by cutting-edge AI and machine learning
          </p>
        </div>

        <div className="grid gap-6 sm:gap-8 md:grid-cols-2 lg:gap-10">
          {features.map((feature, index) => (
            <Card key={index} className="border-2 hover:border-primary/50 hover:shadow-lg transition-all duration-300">
              <CardContent className="p-8">
                <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
                  <feature.icon className="h-7 w-7 text-primary" />
                </div>
                <h3 className="text-xl md:text-2xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed text-base">{feature.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
