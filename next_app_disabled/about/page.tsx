import { Header } from "@/components/landing/header"
import { Footer } from "@/components/landing/footer"
import { Card, CardContent } from "@/components/ui/card"
import { Users, Target, Zap, Shield } from "lucide-react"

export default function AboutPage() {
  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-16 md:py-20 lg:py-24">
        <div className="max-w-3xl mx-auto text-center mb-16 sm:mb-20">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl mb-4 sm:mb-6 text-balance">
            About SNOWFLAKE
          </h1>
          <p className="text-lg text-muted-foreground sm:text-xl text-pretty leading-relaxed">
            We're on a mission to help teams collaborate better and work smarter with innovative SaaS solutions
          </p>
        </div>

        <div className="max-w-4xl mx-auto mb-20 sm:mb-24">
          <Card>
            <CardContent className="p-8 md:p-12">
              <h2 className="text-3xl font-bold mb-6">Our Story</h2>
              <div className="space-y-4 text-muted-foreground leading-relaxed">
                <p>
                  Founded in 2024, SNOWFLAKE was born from a simple idea: work should be easier, not harder. Our
                  founders experienced firsthand the frustration of juggling multiple tools, losing track of important
                  tasks, and watching productivity slip away due to inefficient workflows.
                </p>
                <p>
                  We built SNOWFLAKE to solve these problems. By combining powerful project management features with an
                  intuitive interface, we've created a platform that teams actually enjoy using. Our focus is on
                  simplicity without sacrificing functionality.
                </p>
                <p>
                  Today, thousands of teams around the world use SNOWFLAKE to manage their projects, collaborate
                  effectively, and achieve their goals faster than ever before.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mb-20 sm:mb-24">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl text-center mb-10 sm:mb-12">Our Values</h2>
          <div className="grid gap-6 sm:gap-8 md:grid-cols-2 max-w-5xl mx-auto">
            <Card>
              <CardContent className="p-8">
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-lg bg-primary/10">
                    <Users className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold mb-3">Customer First</h3>
                    <p className="text-muted-foreground leading-relaxed">
                      Every decision we make starts with our customers. We listen, learn, and build features that truly
                      solve real problems.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-8">
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-lg bg-primary/10">
                    <Target className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold mb-3">Focus on Impact</h3>
                    <p className="text-muted-foreground leading-relaxed">
                      We prioritize features and improvements that deliver the most value. No bloat, no unnecessary
                      complexity—just tools that work.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-8">
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-lg bg-primary/10">
                    <Zap className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold mb-3">Innovation</h3>
                    <p className="text-muted-foreground leading-relaxed">
                      We continuously explore new technologies and approaches to make collaboration more seamless and
                      productive.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-8">
                <div className="flex items-start gap-4">
                  <div className="p-3 rounded-lg bg-primary/10">
                    <Shield className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold mb-3">Trust & Security</h3>
                    <p className="text-muted-foreground leading-relaxed">
                      Your data is precious. We employ industry-leading security measures to keep your information safe
                      and private.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-6">Join Our Team</h2>
          <p className="text-xl text-muted-foreground mb-8 text-pretty">
            We're always looking for talented individuals who share our passion for building great products
          </p>
          <div className="flex justify-center gap-4">
            <a
              href="/contact"
              className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 bg-primary text-primary-foreground hover:bg-primary/90 h-10 px-6"
            >
              Get in Touch
            </a>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  )
}
