
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Heart, Users, Clock, Shield } from "lucide-react"

export function HealthImpact() {
  const impacts = [
    {
      icon: Heart,
      title: "Patient Lives Impacted",
      value: "2.3M+",
      description: "Patients benefiting from AI-discovered therapeutics",
      color: "text-red-500",
      bgColor: "bg-red-500/10",
    },
    {
      icon: Clock,
      title: "Time to Discovery",
      value: "18 months",
      description: "Average reduction in drug discovery timeline",
      color: "text-blue-500",
      bgColor: "bg-blue-500/10",
    },
    {
      icon: Users,
      title: "Research Teams",
      value: "500+",
      description: "Biotechnology companies using our platform",
      color: "text-purple-500",
      bgColor: "bg-purple-500/10",
    },
    {
      icon: Shield,
      title: "Safety Predictions",
      value: "96.7%",
      description: "Accuracy in predicting drug safety profiles",
      color: "text-green-500",
      bgColor: "bg-green-500/10",
    },
  ]

  return (
    <section className="py-16 sm:py-20 lg:py-24">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 max-w-7xl">
        <div className="text-center mb-12 sm:mb-16">
          <Badge className="mb-4 sm:mb-6">Real-World Health Impact</Badge>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold mb-4 sm:mb-6 text-balance">
            Advancing Human Health Through AI
          </h2>
          <p className="text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto text-pretty leading-relaxed">
            Our platform accelerates the discovery of life-saving therapeutics, from cancer treatments to diabetes
            management, bringing hope to millions of patients worldwide.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
          {impacts.map((impact) => {
            const Icon = impact.icon
            return (
              <Card key={impact.title} className="border-border hover:shadow-lg transition-all text-center">
                <CardContent className="p-6 sm:p-8">
                  <div
                    className={`w-14 h-14 sm:w-16 sm:h-16 ${impact.bgColor} rounded-2xl flex items-center justify-center mx-auto mb-4`}
                  >
                    <Icon className={`w-7 h-7 sm:w-8 sm:h-8 ${impact.color}`} />
                  </div>
                  <div className={`text-3xl sm:text-4xl font-bold ${impact.color} mb-2`}>{impact.value}</div>
                  <h3 className="font-semibold mb-2 text-sm sm:text-base">{impact.title}</h3>
                  <p className="text-xs sm:text-sm text-muted-foreground">{impact.description}</p>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>
    </section>
  )
}
