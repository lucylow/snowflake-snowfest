import { Card, CardContent } from "@/components/ui/card"
import { Dna, Zap, Brain } from "lucide-react"

const features = [
  {
    icon: Dna,
    title: "Structure Prediction",
    description: "Transform amino acid sequences into accurate 3D protein structures",
    metric: "91% average confidence",
  },
  {
    icon: Zap,
    title: "Rapid Analysis",
    description: "Get structure predictions in minutes instead of months",
    metric: "5-15 min per protein",
  },
  {
    icon: Brain,
    title: "AI-Powered Insights",
    description: "ML analysis of binding sites, druggability, and therapeutic potential",
    metric: "98.3% accuracy",
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

        <div className="grid gap-6 sm:gap-8 md:grid-cols-3 lg:gap-10">
          {features.map((feature, index) => (
            <Card key={index} className="border-2 hover:border-primary/50 hover:shadow-lg transition-all duration-300">
              <CardContent className="p-8">
                <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
                  <feature.icon className="h-7 w-7 text-primary" />
                </div>
                <h3 className="text-xl md:text-2xl font-semibold mb-3">{feature.title}</h3>
                <p className="text-muted-foreground leading-relaxed text-base mb-4">{feature.description}</p>
                <div className="text-2xl font-bold text-primary">{feature.metric}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
