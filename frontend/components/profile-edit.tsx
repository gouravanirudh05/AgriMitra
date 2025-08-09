"use client"

import { useState } from "react"
import { useAuth } from "@/contexts/auth-context"
import { useLanguage } from "@/contexts/language-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Save } from "lucide-react"

import { statesData } from "@/lib/states"

export default function ProfileEditScreen() {
  const { user, updateProfile } = useAuth()
  const { t } = useLanguage()

  const [formData, setFormData] = useState({
    name: user?.name || "",
    age: user?.age?.toString() || "",
    state: user?.state || "",
    district: user?.district || "",
  })

  const handleSave = () => {
    updateProfile({
      ...user,
      name: formData.name,
      age: Number.parseInt(formData.age),
      state: formData.state,
      district: formData.district,
    })
  }

  const stateList = statesData.states.map((s) => s.state)
  const selectedStateObj = statesData.states.find((s) => s.state === formData.state)
  const districtList = selectedStateObj ? selectedStateObj.districts : []

  return (
    <div className="flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          {/* <CardTitle className="text-2xl font-bold text-green-800">{t("profile.editProfile")}</CardTitle> */}
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Name */}
          <div className="space-y-2">
            <Label htmlFor="name">{t("onboarding.name")}</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            />
          </div>

          {/* Age */}
          <div className="space-y-2">
            <Label htmlFor="age">{t("onboarding.age")}</Label>
            <Input
              id="age"
              type="number"
              value={formData.age}
              onChange={(e) => setFormData({ ...formData, age: e.target.value })}
              min="18"
              max="100"
            />
          </div>

          {/* State */}
          <div className="space-y-2">
            <Label>{t("onboarding.state")}</Label>
            <Select
              value={formData.state}
              onValueChange={(value) => setFormData({ ...formData, state: value, district: "" })}
            >
              <SelectTrigger>
                <SelectValue placeholder={t("onboarding.statePlaceholder")} />
              </SelectTrigger>
              <SelectContent>
                {stateList.map((state) => (
                  <SelectItem key={state} value={state}>
                    {state}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* District */}
          {formData.state && (
            <div className="space-y-2">
              <Label>{t("onboarding.district")}</Label>
              <Select
                value={formData.district}
                onValueChange={(value) => setFormData({ ...formData, district: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t("onboarding.districtPlaceholder")} />
                </SelectTrigger>
                <SelectContent>
                  {districtList.map((district) => (
                    <SelectItem key={district} value={district}>
                      {district}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Save Button */}
          <Button className="w-full" onClick={handleSave}>
            <Save className="mr-2 h-4 w-4" /> {t("profile.saveChanges")}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
