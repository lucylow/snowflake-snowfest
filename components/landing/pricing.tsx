"use client"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import { Check } from "lucide-react"
import Link from "next/link"

const plans = [
  {
    name: "Starter",
    price: 29,
    description: "Perfect for individuals and small teams",
    features: ["Up to 10 team members", "100 GB storage", "Basic analytics", "Email support", "Core integrations"],
    cta: "Start Free Trial",
    popular: false,
  },
  {
    name: "Professional",
    price: 79,
    description: "For growing teams that need more power",
    features: [
      "Up to 50 team members",
      "1 TB storage",
      "Advanced analytics",
      "Priority support",
      "All integrations",
      "Custom workflows",
      "API access",
    ],
    cta: "Start Free Trial",
    popular: true,
  },
  {
    name: "Enterprise",
    price: null,
    description: "For large organizations with custom needs",
    features: [
      "Unlimited team members",
      "Unlimited storage",
      "Custom analytics",
      "Dedicated support",
      "Custom integrations",
      "Advanced security",
      "SLA guarantee",
      "Training & onboarding",
    ],
    cta: "Contact Sales",
    popular: false,
  },
]

export function Pricing() {
  return (
    <section id="pricing" className="bg-muted/30">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-24 sm:py-32 md:py-40">
        <div className="text-center mb-16 sm:mb-20">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl mb-4 sm:mb-6 text-balance">
            Simple, transparent pricing
          </h2>
          <p className="text-base text-muted-foreground sm:text-lg md:text-xl max-w-2xl mx-auto text-pretty leading-relaxed">
            Choose the plan that fits your needs. All plans include a 14-day free trial.
          </p>
        </div>

        <div className="grid gap-8 sm:gap-10 lg:grid-cols-3 items-start max-w-6xl mx-auto">
          {plans.map((plan, index) => (
            <Card key={index} className={plan.popular ? "border-primary border-2 relative shadow-xl" : "shadow-md"}>
              {plan.popular && (
                <div className="absolute -top-5 left-1/2 -translate-x-1/2">
                  <span className="bg-primary text-primary-foreground text-sm font-semibold px-4 py-1.5 rounded-full shadow-lg">
                    Most Popular
                  </span>
                </div>
              )}
              <CardHeader className="text-center pb-8 pt-8">
                <h3 className="text-2xl md:text-3xl font-bold mb-3">{plan.name}</h3>
                <p className="text-sm md:text-base text-muted-foreground mb-6 px-2">{plan.description}</p>
                <div className="text-4xl md:text-5xl font-bold">
                  {plan.price ? (
                    <>
                      ${plan.price}
                      <span className="text-lg md:text-xl font-normal text-muted-foreground">/month</span>
                    </>
                  ) : (
                    <span className="text-3xl">Custom</span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="px-6 pb-6">
                <ul className="space-y-4">
                  {plan.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-start gap-3">
                      <Check className="h-5 w-5 text-primary shrink-0 mt-1" />
                      <span className="text-sm md:text-base leading-relaxed">{feature}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
              <CardFooter className="px-6 pb-6">
                <Link href={plan.price === null ? "/contact" : "/dashboard"} className="w-full">
                  <Button className="w-full" variant={plan.popular ? "default" : "outline"}>
                    {plan.cta}
                  </Button>
                </Link>
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
