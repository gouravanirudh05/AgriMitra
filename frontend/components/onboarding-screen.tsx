"use client"

import { useState } from "react"
import { useAuth } from "@/contexts/auth-context"
import { useLanguage } from "@/contexts/language-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Progress } from "@/components/ui/progress"
import { ArrowRight, User, MapPin, CheckCircle, Globe } from "lucide-react"

// Example JSON data
import {statesData} from "../lib/states.js"

export default function OnboardingScreen() {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    name: "",
    age: "",
    state: "",
    district: "",
  })

  const { updateProfile } = useAuth()
  const { t, changeLanguage, currentLanguage } = useLanguage()

  const handleNext = () => {
    if (step < 2) {
      setStep(step + 1)
    } else {
      updateProfile({
        name: formData.name,
        age: Number.parseInt(formData.age),
        state: formData.state,
        district: formData.district,
        isOnboarded: true,
      })
    }
  }

  const isStepValid = () => {
    if (step === 1) {
      return formData.name.trim() && formData.age.trim() && Number.parseInt(formData.age) >= 18
    }
    return formData.state && formData.district.trim()
  }

  // Get list of states from JSON
  const stateList = statesData.states.map((s) => s.state)

  // Get districts based on selected state
  const selectedStateObj = statesData.states.find((s) => s.state === formData.state)
  const districtList = selectedStateObj ? selectedStateObj.districts : []

  return (
    <div className="flex items-center justify-center min-h-screen p-4 bg-gradient-to-br from-green-50 to-blue-50">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            <div className={`p-4 rounded-full ${step === 1 ? "bg-blue-100" : "bg-green-100"}`}>
              {step === 1 ? <User className="h-8 w-8 text-blue-600" /> : <MapPin className="h-8 w-8 text-green-600" />}
            </div>
          </div>
          <CardTitle className="text-2xl font-bold text-green-800">{t("onboarding.welcome")}</CardTitle>
          <CardDescription className="text-base">
            {step === 1 ? t("onboarding.personalInfo") : t("onboarding.location")}
          </CardDescription>
          <div className="mt-4 space-y-2">
            <Progress value={(step / 2) * 100} className="h-2" />
            <p className="text-sm text-gray-500">
              {t("onboarding.step")} {step} {t("onboarding.of")} 2
            </p>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {step === 1 ? (
            <div className="space-y-4">
              {/* Language button */}
              <div className="flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => changeLanguage(currentLanguage === "en" ? "hi" : "en")}
                >
                  <Globe className="mr-2 h-4 w-4" />
                  {currentLanguage}
                </Button>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name" className="text-base font-medium">
                  {t("onboarding.name")} *
                </Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="h-12 text-base"
                  placeholder={t("onboarding.namePlaceholder")}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="age" className="text-base font-medium">
                  {t("onboarding.age")} *
                </Label>
                <Input
                  id="age"
                  type="number"
                  value={formData.age}
                  onChange={(e) => setFormData({ ...formData, age: e.target.value })}
                  className="h-12 text-base"
                  placeholder={t("onboarding.agePlaceholder")}
                  min="18"
                  max="100"
                />
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="state" className="text-base font-medium">
                  {t("onboarding.state")} *
                </Label>
                <Select
                  value={formData.state}
                  onValueChange={(value) => setFormData({ ...formData, state: value, district: "" })}
                >
                  <SelectTrigger className="h-12 text-base">
                    <SelectValue placeholder={t("onboarding.statePlaceholder")} />
                  </SelectTrigger>
                  <SelectContent>
                    {stateList.map((state) => (
                      <SelectItem key={state} value={state} className="text-base">
                        {state}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {formData.state && (
                <div className="space-y-2">
                  <Label htmlFor="district" className="text-base font-medium">
                    {t("onboarding.district")} *
                  </Label>
                  <Select
                    value={formData.district}
                    onValueChange={(value) => setFormData({ ...formData, district: value })}
                  >
                    <SelectTrigger className="h-12 text-base">
                      <SelectValue placeholder={t("onboarding.districtPlaceholder")} />
                    </SelectTrigger>
                    <SelectContent>
                      {districtList.map((district) => (
                        <SelectItem key={district} value={district} className="text-base">
                          {district}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          )}

          <Button onClick={handleNext} className="w-full h-12 text-base" disabled={!isStepValid()}>
            {step === 2 ? (
              <>
                <CheckCircle className="mr-2 h-5 w-5" />
                {t("onboarding.complete")}
              </>
            ) : (
              <>
                {t("onboarding.next")}
                <ArrowRight className="ml-2 h-5 w-5" />
              </>
            )}
          </Button>
          {step === 1 && <p className="text-sm text-gray-500 text-center">{t("onboarding.privacy")}</p>}
        </CardContent>
      </Card>
    </div>
  )
}
