"use client"

import { useState } from "react"
import { useLanguage } from "@/contexts/language-context"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import LanguageSelector from "./language-selector"
import AuthScreen from "./auth-screen"
import { Sprout, MessageSquare, Mic, Users, Globe, ArrowRight, CheckCircle } from "lucide-react"

export default function LandingPage() {
  const [showAuth, setShowAuth] = useState(false)
  const { t } = useLanguage()

  if (showAuth) {
    return <AuthScreen onBack={() => setShowAuth(false)} />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-blue-50 to-emerald-50">
      {/* Header */}
      <header className="container mx-auto px-4 py-6 flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <div className="p-2 bg-green-600 rounded-lg">
            <Sprout className="h-6 w-6 text-white" />
          </div>
          <span className="text-2xl font-bold text-green-800">AgriMitra</span>
        </div>
        <LanguageSelector />
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-16 text-center">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-6xl font-bold text-gray-900 mb-6">{t("landing.hero.title")}</h1>
          <p className="text-xl md:text-2xl text-gray-600 mb-8">{t("landing.hero.subtitle")}</p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="text-lg px-8 py-6" onClick={() => setShowAuth(true)}>
              {t("landing.hero.getStarted")}
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button variant="outline" size="lg" className="text-lg px-8 py-6 bg-transparent">
              {t("landing.hero.learnMore")}
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">{t("landing.features.title")}</h2>
          <p className="text-xl text-gray-600">{t("landing.features.subtitle")}</p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="text-center">
              <div className="mx-auto mb-4 p-3 bg-blue-100 rounded-full w-fit">
                <MessageSquare className="h-8 w-8 text-blue-600" />
              </div>
              <CardTitle className="text-xl">{t("landing.features.chat.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-center text-base">
                {t("landing.features.chat.description")}
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="text-center">
              <div className="mx-auto mb-4 p-3 bg-green-100 rounded-full w-fit">
                <Mic className="h-8 w-8 text-green-600" />
              </div>
              <CardTitle className="text-xl">{t("landing.features.voice.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-center text-base">
                {t("landing.features.voice.description")}
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader className="text-center">
              <div className="mx-auto mb-4 p-3 bg-purple-100 rounded-full w-fit">
                <Globe className="h-8 w-8 text-purple-600" />
              </div>
              <CardTitle className="text-xl">{t("landing.features.multilingual.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="text-center text-base">
                {t("landing.features.multilingual.description")}
              </CardDescription>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="bg-white py-16">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">{t("landing.benefits.title")}</h2>
          </div>

          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <div className="flex items-start space-x-4">
                <CheckCircle className="h-6 w-6 text-green-600 mt-1 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold mb-2">{t("landing.benefits.expert.title")}</h3>
                  <p className="text-gray-600">{t("landing.benefits.expert.description")}</p>
                </div>
              </div>
              <div className="flex items-start space-x-4">
                <CheckCircle className="h-6 w-6 text-green-600 mt-1 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold mb-2">{t("landing.benefits.available.title")}</h3>
                  <p className="text-gray-600">{t("landing.benefits.available.description")}</p>
                </div>
              </div>
              <div className="flex items-start space-x-4">
                <CheckCircle className="h-6 w-6 text-green-600 mt-1 flex-shrink-0" />
                <div>
                  <h3 className="text-lg font-semibold mb-2">{t("landing.benefits.personalized.title")}</h3>
                  <p className="text-gray-600">{t("landing.benefits.personalized.description")}</p>
                </div>
              </div>
            </div>
            <div className="bg-gradient-to-br from-green-100 to-blue-100 rounded-2xl p-8 text-center">
              <Users className="h-16 w-16 text-green-600 mx-auto mb-4" />
              <h3 className="text-2xl font-bold text-gray-900 mb-2">{t("landing.benefits.farmers")}</h3>
              <p className="text-gray-600">{t("landing.benefits.helping")}</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-16 text-center">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">{t("landing.cta.title")}</h2>
          <p className="text-xl text-gray-600 mb-8">{t("landing.cta.subtitle")}</p>
          <Button size="lg" className="text-lg px-8 py-6" onClick={() => setShowAuth(true)}>
            {t("landing.cta.button")}
            <ArrowRight className="ml-2 h-5 w-5" />
          </Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-8">
        <div className="container mx-auto px-4 text-center">
          <div className="flex items-center justify-center space-x-2 mb-4">
            <div className="p-2 bg-green-600 rounded-lg">
              <Sprout className="h-5 w-5 text-white" />
            </div>
            <span className="text-xl font-bold">AgriMitra</span>
          </div>
          <p className="text-gray-400">{t("landing.footer.copyright")}</p>
        </div>
      </footer>
    </div>
  )
}
