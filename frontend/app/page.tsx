"use client"

import { useAuth } from "@/contexts/auth-context"
import { useLanguage } from "@/contexts/language-context"
import OnboardingScreen from "@/components/onboarding-screen"
import ChatScreen from "@/components/chat-screen"
import LandingPage from "@/components/landing-page"
import { Loader2 } from "lucide-react"

export default function Home() {
  const { user, isLoading } = useAuth()
  const { t } = useLanguage()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">{t("common.loading")}</span>
      </div>
    )
  }

  // Show landing page if no user
  if (!user) {
    return <LandingPage />
  }

  // Show onboarding if user not onboarded
  if (!user.isOnboarded) {
    return <OnboardingScreen />
  }

  // Show main chat interface
  return <ChatScreen />
}
