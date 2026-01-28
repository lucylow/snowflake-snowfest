
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dna, Zap, Brain, TrendingUp, CheckCircle2 } from "lucide-react"
import { Progress } from "@/components/ui/progress"

export function AlphaFoldShowcase() {
  const features = [
    {
      icon: Dna,
      title: "Structure Prediction",
      description: "Transform amino acid sequences into accurate 3D protein structures",
      metric: "91% average confidence",
      color: "text-blue-500",
      bgColor: "bg-blue-500/10",
    },
    {
      icon: Zap,
      title: "Rapid Analysis",
      description: "Get structure predictions in minutes instead of months",
      metric: "5-15 min per protein",
      color: "text-purple-500",
      bgColor: "bg-purple-500/10",
    },
    {
      icon: Brain,
      title: "AI-Powered Insights",
      description: "ML analysis of binding sites, druggability, and therapeutic potential",
      metric: "98.3% accuracy",
      color: "text-green-500",
      bgColor: "bg-green-500/10",
    },
  ]

  const workflow = [
    { step: 1, title: "Input Sequence", status: "complete" },
    { step: 2, title: "AlphaFold Prediction", status: "complete" },
    { step: 3, title: "Quality Assessment", status: "complete" },
    { step: 4, title: "Binding Site Analysis", status: "complete" },
    { step: 5, title: "Molecular Docking", status: "complete" },
    { step: 6, title: "Therapeutic Insights", status: "complete" },
  ]

  return (
    <section className="py-16 sm:py-20 lg:py-24 bg-gradient-to-b from-background to-muted/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl">
        <div className="text-center mb-12 sm:mb-16">
          <Badge className="mb-4 sm:mb-6 bg-gradient-to-r from-blue-500 to-purple-500">Powered by AlphaFold</Badge>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4 sm:mb-6 text-balance">
            From Sequence to Therapeutic Candidate
          </h2>
          <p className="text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto text-pretty leading-relaxed">
            Leverage state-of-the-art AI to predict protein structures with atomic accuracy, then screen thousands of
            compounds to discover novel therapeutics for human health.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 sm:gap-8 mb-12">
          {features.map((feature) => {
            const Icon = feature.icon
            return (
              <Card key={feature.title} className="border-border hover:shadow-lg transition-all">
                <CardContent className="p-6 sm:p-8">
                  <div
                    className={`w-14 h-14 sm:w-16 sm:h-16 ${feature.bgColor} rounded-2xl flex items-center justify-center mb-6`}
                  >
                    <Icon className={`w-7 h-7 sm:w-8 sm:h-8 ${feature.color}`} />
                  </div>
                  <h3 className="text-lg sm:text-xl font-bold mb-3">{feature.title}</h3>
                  <p className="text-sm sm:text-base text-muted-foreground mb-4">{feature.description}</p>
                  <div className="flex items-center gap-2">
                    <TrendingUp className={`w-4 h-4 ${feature.color}`} />
                    <span className={`text-sm font-semibold ${feature.color}`}>{feature.metric}</span>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        <Card className="border-border shadow-lg">
          <CardHeader>
            <CardTitle className="text-2xl sm:text-3xl">Complete Drug Discovery Workflow</CardTitle>
            <CardDescription className="text-base">
              End-to-end AI pipeline from protein sequence to clinical insights
            </CardDescription>
          </CardHeader>
          <CardContent className="p-6 sm:p-8">
            <div className="space-y-4">
              {workflow.map((item, index) => (
                <div key={item.step} className="flex items-center gap-4">
                  <div className="flex items-center gap-3 flex-1">
                    <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center flex-shrink-0">
                      <CheckCircle2 className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-semibold text-sm sm:text-base">{item.title}</span>
                        <Badge variant="secondary" className="text-xs">
                          Complete
                        </Badge>
                      </div>
                      <Progress value={100} className="h-2" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
