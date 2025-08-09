"use client"

import type React from "react"
import { createContext, useContext, useState, useEffect } from "react"

type Language = "en" | "hi" | "kn" | "mr"

interface LanguageContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: string) => string
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

const translations = {
  en: {
    // Auth
    "auth.welcome": "Welcome to AgriMitra",
    "auth.login": "Login",
    "auth.register": "Register",
    "auth.email": "Email",
    "auth.mobile": "Mobile Number",
    "auth.password": "Password",
    "auth.confirmPassword": "Confirm Password",
    "auth.loginButton": "Sign In",
    "auth.registerButton": "Create Account",
    "auth.switchToRegister": "Don't have an account? Register",
    "auth.switchToLogin": "Already have an account? Login",

    // Onboarding
    "onboarding.welcome": "Welcome, Farmer!",
    "onboarding.personalInfo": "Personal Information",
    "onboarding.name": "Full Name",
    "onboarding.age": "Age",
    "onboarding.location": "Location Details",
    "onboarding.state": "State",
    "onboarding.district": "District",
    "onboarding.next": "Next",
    "onboarding.complete": "Complete Setup",
    "onboarding.step": "Step",
    "onboarding.of": "of",
    "onboarding.namePlaceholder": "Enter your full name",
    "onboarding.agePlaceholder": "Enter your age",
    "onboarding.statePlaceholder": "Select your state",
    "onboarding.districtPlaceholder": "Enter your district",
    "onboarding.privacy": "Your information is secure and will only be used to provide better farming advice.",

    // Chat
    "chat.title": "Ask Your Question",
    "chat.placeholder": "Type your farming question...",
    "chat.voiceButton": "Hold to speak",
    "chat.send": "Send",
    "chat.listening": "Listening...",
    "chat.conversations": "Previous Conversations",
    "chat.newChat": "New Chat",
    "chat.welcome.title": "How can I help you today?",
    "chat.welcome.subtitle": "Choose how you'd like to ask your farming question",
    "chat.welcome.voice": "Speak",
    "chat.welcome.voiceDesc": "Hold to record",
    "chat.welcome.type": "Type",
    "chat.welcome.typeDesc": "Use keyboard",
    "chat.welcome.examples": "Try asking about:",
    "chat.thinking": "Thinking...",
    "chat.stopListening": "Stop Recording",
    "chat.typeQuestion": "Type Your Question",

    // Common
    "common.selectLanguage": "Select Language",
    "common.loading": "Loading...",
    "common.error": "Something went wrong",
    "common.retry": "Retry",
    "common.cancel": "Cancel",

    // Landing page
    "landing.hero.title": "AI-Powered Assistant for Modern Farmers",
    "landing.hero.subtitle": "Get instant answers to your farming questions in your native language",
    "landing.hero.getStarted": "Get Started",
    "landing.hero.learnMore": "Learn More",

    "landing.features.title": "Why Choose AgriMitra?",
    "landing.features.subtitle": "Empowering farmers with intelligent technology",
    "landing.features.chat.title": "Smart Chat Assistant",
    "landing.features.chat.description":
      "Ask questions about crops, weather, diseases, and get expert advice instantly",
    "landing.features.voice.title": "Voice Input",
    "landing.features.voice.description": "Speak naturally in your language - no need to type",
    "landing.features.multilingual.title": "Multilingual Support",
    "landing.features.multilingual.description": "Available in English, Hindi, Kannada, and Marathi",

    "landing.benefits.title": "Benefits for Farmers",
    "landing.benefits.expert.title": "Expert Knowledge",
    "landing.benefits.expert.description": "Access to agricultural expertise anytime, anywhere",
    "landing.benefits.available.title": "24/7 Available",
    "landing.benefits.available.description": "Get help whenever you need it, day or night",
    "landing.benefits.personalized.title": "Personalized Advice",
    "landing.benefits.personalized.description": "Recommendations based on your location and crops",
    "landing.benefits.farmers": "10,000+",
    "landing.benefits.helping": "Farmers already using AgriMitra",

    "landing.cta.title": "Ready to Transform Your Farming?",
    "landing.cta.subtitle": "Join thousands of farmers who are already benefiting from AI-powered assistance",
    "landing.cta.button": "Start Your Journey",

    "landing.footer.copyright": "© 2024 AgriMitra. All rights reserved.",

    // Nav
    "nav.dashboard": "Dashboard",
    "nav.openprofile": "Open Profile",
    "nav.settings": "Settings",
    "nav.help": "Help",
    "nav.logout": "Logout",

    "profile.editProfile": "Edit Profile",
    "profile.saveChanges": "Save Changes",
    "profile.name": "Name",
    "profile.age": "Age",
    "profile.state": "State",
    "profile.district": "District",
  },
  hi: {
    // Auth
    "auth.welcome": "फार्मएजेंट में आपका स्वागत है",
    "auth.login": "लॉगिन",
    "auth.register": "पंजीकरण",
    "auth.email": "ईमेल",
    "auth.mobile": "मोबाइल नंबर",
    "auth.password": "पासवर्ड",
    "auth.confirmPassword": "पासवर्ड की पुष्टि करें",
    "auth.loginButton": "साइन इन",
    "auth.registerButton": "खाता बनाएं",
    "auth.switchToRegister": "खाता नहीं है? पंजीकरण करें",
    "auth.switchToLogin": "पहले से खाता है? लॉगिन करें",

    // Onboarding
    "onboarding.welcome": "स्वागत है, किसान!",
    "onboarding.personalInfo": "व्यक्तिगत जानकारी",
    "onboarding.name": "पूरा नाम",
    "onboarding.age": "उम्र",
    "onboarding.location": "स्थान विवरण",
    "onboarding.state": "राज्य",
    "onboarding.district": "जिला",
    "onboarding.next": "अगला",
    "onboarding.complete": "सेटअप पूरा करें",
    "onboarding.step": "चरण",
    "onboarding.of": "का",
    "onboarding.namePlaceholder": "अपना पूरा नाम दर्ज करें",
    "onboarding.agePlaceholder": "अपनी उम्र दर्ज करें",
    "onboarding.statePlaceholder": "अपना राज्य चुनें",
    "onboarding.districtPlaceholder": "अपना जिला दर्ज करें",
    "onboarding.privacy": "आपकी जानकारी सुरक्षित है और केवल बेहतर कृषि सलाह प्रदान करने के लिए उपयोग की जाएगी।",

    // Chat
    "chat.title": "अपना प्रश्न पूछें",
    "chat.placeholder": "अपना खेती का सवाल टाइप करें...",
    "chat.voiceButton": "बोलने के लिए दबाएं",
    "chat.send": "भेजें",
    "chat.listening": "सुन रहे हैं...",
    "chat.conversations": "पिछली बातचीत",
    "chat.newChat": "नई चैट",
    "chat.welcome.title": "आज मैं आपकी कैसे मदद कर सकता हूं?",
    "chat.welcome.subtitle": "चुनें कि आप अपना खेती का सवाल कैसे पूछना चाहते हैं",
    "chat.welcome.voice": "बोलें",
    "chat.welcome.voiceDesc": "रिकॉर्ड करने के लिए दबाएं",
    "chat.welcome.type": "टाइप करें",
    "chat.welcome.typeDesc": "कीबोर्ड का उपयोग करें",
    "chat.welcome.examples": "इन विषयों पर पूछें:",
    "chat.thinking": "सोच रहा हूं...",
    "chat.stopListening": "रिकॉर्डिंग बंद करें",
    "chat.typeQuestion": "अपना प्रश्न टाइप करें",

    // Common
    "common.selectLanguage": "भाषा चुनें",
    "common.loading": "लोड हो रहा है...",
    "common.error": "कुछ गलत हुआ",
    "common.retry": "पुनः प्रयास",
    "common.cancel": "रद्द करें",
    

    // Landing page
    "landing.hero.title": "आधुनिक किसानों के लिए AI-संचालित सहायक",
    "landing.hero.subtitle": "अपनी मातृभाषा में खेती के सवालों के तुरंत जवाब पाएं",
    "landing.hero.getStarted": "शुरू करें",
    "landing.hero.learnMore": "और जानें",

    "landing.features.title": "फार्मएजेंट क्यों चुनें?",
    "landing.features.subtitle": "बुद्धिमान तकनीक के साथ किसानों को सशक्त बनाना",
    "landing.features.chat.title": "स्मार्ट चैट सहायक",
    "landing.features.chat.description": "फसल, मौसम, बीमारियों के बारे में सवाल पूछें और तुरंत विशेषज्ञ सलाह पाएं",
    "landing.features.voice.title": "आवाज इनपुट",
    "landing.features.voice.description": "अपनी भाषा में स्वाभाविक रूप से बोलें - टाइप करने की जरूरत नहीं",
    "landing.features.multilingual.title": "बहुभाषी समर्थन",
    "landing.features.multilingual.description": "अंग्रेजी, हिंदी, कन्नड़ और मराठी में उपलब्ध",

    "landing.benefits.title": "किसानों के लिए फायदे",
    "landing.benefits.expert.title": "विशेषज्ञ ज्ञान",
    "landing.benefits.expert.description": "कभी भी, कहीं भी कृषि विशेषज्ञता तक पहुंच",
    "landing.benefits.available.title": "24/7 उपलब्ध",
    "landing.benefits.available.description": "जब भी आपको जरूरत हो, दिन हो या रात, मदद पाएं",
    "landing.benefits.personalized.title": "व्यक्तिगत सलाह",
    "landing.benefits.personalized.description": "आपके स्थान और फसलों के आधार पर सिफारिशें",
    "landing.benefits.farmers": "10,000+",
    "landing.benefits.helping": "किसान पहले से ही फार्मएजेंट का उपयोग कर रहे हैं",

    "landing.cta.title": "अपनी खेती को बदलने के लिए तैयार हैं?",
    "landing.cta.subtitle": "हजारों किसानों में शामिल हों जो पहले से ही AI-संचालित सहायता से लाभ उठा रहे हैं",
    "landing.cta.button": "अपनी यात्रा शुरू करें",

    "landing.footer.copyright": "© 2024 फार्मएजेंट। सभी अधिकार सुरक्षित।",

    // Nav
    "nav.dashboard": "डैशबोर्ड",
    "nav.openprofile": "प्रोफाइल खोलें",
    "nav.settings": "सेटिंग्स",
    "nav.help": "सहायता",
    "nav.logout": "लॉगआउट",

    // Profile
    "profile.editProfile": "प्रोफाइल संपादित करें",
    "profile.saveChanges": "परिवर्तनों को सहेजें",
    "profile.name": "नाम",
    "profile.age": "उम्र",
    "profile.state": "राज्य",
    "profile.district": "जिल्हा",
  },
  kn: {
    // Auth
    "auth.welcome": "ಫಾರ್ಮ್‌ಏಜೆಂಟ್‌ಗೆ ಸ್ವಾಗತ",
    "auth.login": "ಲಾಗಿನ್",
    "auth.register": "ನೋಂದಣಿ",
    "auth.email": "ಇಮೇಲ್",
    "auth.mobile": "ಮೊಬೈಲ್ ಸಂಖ್ಯೆ",
    "auth.password": "ಪಾಸ್‌ವರ್ಡ್",
    "auth.confirmPassword": "ಪಾಸ್‌ವರ್ಡ್ ದೃಢೀಕರಿಸಿ",
    "auth.loginButton": "ಸೈನ್ ಇನ್",
    "auth.registerButton": "ಖಾತೆ ರಚಿಸಿ",
    "auth.switchToRegister": "ಖಾತೆ ಇಲ್ಲವೇ? ನೋಂದಣಿ ಮಾಡಿ",
    "auth.switchToLogin": "ಈಗಾಗಲೇ ಖಾತೆ ಇದೆಯೇ? ಲಾಗಿನ್",

    // Onboarding
    "onboarding.welcome": "ಸ್ವಾಗತ, ರೈತರೇ!",
    "onboarding.personalInfo": "ವೈಯಕ್ತಿಕ ಮಾಹಿತಿ",
    "onboarding.name": "ಪೂರ್ಣ ಹೆಸರು",
    "onboarding.age": "ವಯಸ್ಸು",
    "onboarding.location": "ಸ್ಥಳದ ವಿವರಗಳು",
    "onboarding.state": "ರಾಜ್ಯ",
    "onboarding.district": "ಜಿಲ್ಲೆ",
    "onboarding.next": "ಮುಂದೆ",
    "onboarding.complete": "ಸೆಟಪ್ ಪೂರ್ಣಗೊಳಿಸಿ",
    "onboarding.step": "ಹಂತ",
    "onboarding.of": "ರ",
    "onboarding.namePlaceholder": "ನಿಮ್ಮ ಪೂರ್ಣ ಹೆಸರನ್ನು ನಮೂದಿಸಿ",
    "onboarding.agePlaceholder": "ನಿಮ್ಮ ವಯಸ್ಸನ್ನು ನಮೂದಿಸಿ",
    "onboarding.statePlaceholder": "ನಿಮ್ಮ ರಾಜ್ಯವನ್ನು ಆಯ್ಕೆಮಾಡಿ",
    "onboarding.districtPlaceholder": "ನಿಮ್ಮ ಜಿಲ್ಲೆಯನ್ನು ನಮೂದಿಸಿ",
    "onboarding.privacy": "ನಿಮ್ಮ ಮಾಹಿತಿಯು ಸುರಕ್ಷಿತವಾಗಿದೆ ಮತ್ತು ಉತ್ತಮ ಕೃಷಿ ಸಲಹೆ ನೀಡಲು ಮಾತ್ರ ಬಳಸಲಾಗುತ್ತದೆ।",

    // Chat
    "chat.title": "ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಕೇಳಿ",
    "chat.placeholder": "ನಿಮ್ಮ ಕೃಷಿ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ...",
    "chat.voiceButton": "ಮಾತನಾಡಲು ಹಿಡಿದುಕೊಳ್ಳಿ",
    "chat.send": "ಕಳುಹಿಸಿ",
    "chat.listening": "ಕೇಳುತ್ತಿದೆ...",
    "chat.conversations": "ಹಿಂದಿನ ಸಂಭಾಷಣೆಗಳು",
    "chat.newChat": "ಹೊಸ ಚಾಟ್",
    "chat.welcome.title": "ಇಂದು ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?",
    "chat.welcome.subtitle": "ನಿಮ್ಮ ಕೃಷಿ ಪ್ರಶ್ನೆಯನ್ನು ಹೇಗೆ ಕೇಳಬೇಕೆಂದು ಆಯ್ಕೆಮಾಡಿ",
    "chat.welcome.voice": "ಮಾತನಾಡಿ",
    "chat.welcome.voiceDesc": "ರೆಕಾರ್ಡ್ ಮಾಡಲು ಹಿಡಿದುಕೊಳ್ಳಿ",
    "chat.welcome.type": "ಟೈಪ್ ಮಾಡಿ",
    "chat.welcome.typeDesc": "ಕೀಬೋರ್ಡ್ ಬಳಸಿ",
    "chat.welcome.examples": "ಇವುಗಳ ಬಗ್ಗೆ ಕೇಳಿ:",
    "chat.thinking": "ಯೋಚಿಸುತ್ತಿದೆ...",
    "chat.stopListening": "ರೆಕಾರ್ಡಿಂಗ್ ನಿಲ್ಲಿಸಿ",
    "chat.typeQuestion": "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ",

    // Common
    "common.selectLanguage": "ಭಾಷೆ ಆಯ್ಕೆಮಾಡಿ",
    "common.loading": "ಲೋಡ್ ಆಗುತ್ತಿದೆ...",
    "common.error": "ಏನೋ ತಪ್ಪಾಗಿದೆ",
    "common.retry": "ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ",
    "common.cancel": "ರದ್ದುಮಾಡಿ",

    // Landing page
    "landing.hero.title": "ಆಧುನಿಕ ರೈತರಿಗಾಗಿ AI-ಚಾಲಿತ ಸಹಾಯಕ",
    "landing.hero.subtitle": "ನಿಮ್ಮ ಮಾತೃಭಾಷೆಯಲ್ಲಿ ಕೃಷಿ ಪ್ರಶ್ನೆಗಳಿಗೆ ತ್ವರಿತ ಉತ್ತರಗಳನ್ನು ಪಡೆಯಿರಿ",
    "landing.hero.getStarted": "ಪ್ರಾರಂಭಿಸಿ",
    "landing.hero.learnMore": "ಇನ್ನಷ್ಟು ತಿಳಿಯಿರಿ",

    "landing.features.title": "ಫಾರ್ಮ್‌ಏಜೆಂಟ್ ಅನ್ನು ಏಕೆ ಆಯ್ಕೆ ಮಾಡಬೇಕು?",
    "landing.features.subtitle": "ಬುದ್ಧಿವಂತ ತಂತ್ರಜ್ಞಾನದೊಂದಿಗೆ ರೈತರನ್ನು ಸಶಕ್ತಗೊಳಿಸುವುದು",
    "landing.features.chat.title": "ಸ್ಮಾರ್ಟ್ ಚಾಟ್ ಸಹಾಯಕ",
    "landing.features.chat.description": "ಬೆಳೆಗಳು, ಹವಾಮಾನ, ರೋಗಗಳ ಬಗ್ಗೆ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ ಮತ್ತು ತಕ್ಷಣ ತಜ್ಞರ ಸಲಹೆ ಪಡೆಯಿರಿ",
    "landing.features.voice.title": "ಧ್ವನಿ ಇನ್‌ಪುಟ್",
    "landing.features.voice.description": "ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ ಸ್ವಾಭಾವಿಕವಾಗಿ ಮಾತನಾಡಿ - ಟೈಪ್ ಮಾಡುವ ಅಗತ್ಯವಿಲ್ಲ",
    "landing.features.multilingual.title": "ಬಹುಭಾಷಾ ಬೆಂಬಲ",
    "landing.features.multilingual.description": "ಇಂಗ್ಲಿಷ್, ಹಿಂದಿ, ಕನ್ನಡ ಮತ್ತು ಮರಾಠಿಯಲ್ಲಿ ಲಭ್ಯವಿದೆ",

    "landing.benefits.title": "ರೈತರಿಗೆ ಪ್ರಯೋಜನಗಳು",
    "landing.benefits.expert.title": "ತಜ್ಞರ ಜ್ಞಾನ",
    "landing.benefits.expert.description": "ಯಾವಾಗ ಬೇಕಾದರೂ, ಎಲ್ಲಿ ಬೇಕಾದರೂ ಕೃಷಿ ಪರಿಣತಿಗೆ ಪ್ರವೇಶ",
    "landing.benefits.available.title": "24/7 ಲಭ್ಯ",
    "landing.benefits.available.description": "ನಿಮಗೆ ಯಾವಾಗ ಬೇಕಾದರೂ, ಹಗಲು ಅಥವಾ ರಾತ್ರಿ, ಸಹಾಯ ಪಡೆಯಿರಿ",
    "landing.benefits.personalized.title": "ವೈಯಕ್ತಿಕ ಸಲಹೆ",
    "landing.benefits.personalized.description": "ನಿಮ್ಮ ಸ್ಥಳ ಮತ್ತು ಬೆಳೆಗಳ ಆಧಾರದ ಮೇಲೆ ಶಿಫಾರಸುಗಳು",
    "landing.benefits.farmers": "10,000+",
    "landing.benefits.helping": "ರೈತರು ಈಗಾಗಲೇ ಫಾರ್ಮ್‌ಏಜೆಂಟ್ ಬಳಸುತ್ತಿದ್ದಾರೆ",

    "landing.cta.title": "ನಿಮ್ಮ ಕೃಷಿಯನ್ನು ಪರಿವರ್ತಿಸಲು ಸಿದ್ಧರಿದ್ದೀರಾ?",
    "landing.cta.subtitle": "AI-ಚಾಲಿತ ಸಹಾಯದಿಂದ ಈಗಾಗಲೇ ಪ್ರಯೋಜನ ಪಡೆಯುತ್ತಿರುವ ಸಾವಿರಾರು ರೈತರೊಂದಿಗೆ ಸೇರಿಕೊಳ್ಳಿ",
    "landing.cta.button": "ನಿಮ್ಮ ಪ್ರಯಾಣ ಪ್ರಾರಂಭಿಸಿ",

    "landing.footer.copyright": "© 2024 ಫಾರ್ಮ್‌ಏಜೆಂಟ್. ಎಲ್ಲಾ ಹಕ್ಕುಗಳನ್ನು ಕಾಯ್ದಿರಿಸಲಾಗಿದೆ.",

    // Nav
    "nav.dashboard": "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",
    "nav.settings": "ಸೆಟ್ಟಿಂಗ್‌ಗಳು",
    "nav.help": "ಸಹಾಯ",
    "nav.logout": "ಲಾಗ್‌ಔಟ್",
  },
  mr: {
    // Auth
    "auth.welcome": "फार्मएजेंटमध्ये आपले स्वागत",
    "auth.login": "लॉगिन",
    "auth.register": "नोंदणी",
    "auth.email": "ईमेल",
    "auth.mobile": "मोबाइल नंबर",
    "auth.password": "पासवर्ड",
    "auth.confirmPassword": "पासवर्डची पुष्टी करा",
    "auth.loginButton": "साइन इन",
    "auth.registerButton": "खाते तयार करा",
    "auth.switchToRegister": "खाते नाही? नोंदणी करा",
    "auth.switchToLogin": "आधीच खाते आहे? लॉगिन करा",

    // Onboarding
    "onboarding.welcome": "स्वागत, शेतकरी!",
    "onboarding.personalInfo": "वैयक्तिक माहिती",
    "onboarding.name": "पूर्ण नाव",
    "onboarding.age": "वय",
    "onboarding.location": "स्थान तपशील",
    "onboarding.state": "राज्य",
    "onboarding.district": "जिल्हा",
    "onboarding.next": "पुढे",
    "onboarding.complete": "सेटअप पूर्ण करा",
    "onboarding.step": "पायरी",
    "onboarding.of": "चा",
    "onboarding.namePlaceholder": "तुमचे पूर्ण नाव टाका",
    "onboarding.agePlaceholder": "तुमचे वय टाका",
    "onboarding.statePlaceholder": "तुमचे राज्य निवडा",
    "onboarding.districtPlaceholder": "तुमचा जिल्हा टाका",
    "onboarding.privacy": "तुमची माहिती सुरक्षित आहे आणि फक्त चांगला शेती सल्ला देण्यासाठी वापरली जाईल।",

    // Chat
    "chat.title": "तुमचा प्रश्न विचारा",
    "chat.placeholder": "तुमचा शेतीचा प्रश्न टाइप करा...",
    "chat.voiceButton": "बोलण्यासाठी दाबा",
    "chat.send": "पाठवा",
    "chat.listening": "ऐकत आहे...",
    "chat.conversations": "मागील संभाषणे",
    "chat.newChat": "नवीन चॅट",
    "chat.welcome.title": "आज मी तुमची कशी मदत करू शकतो?",
    "chat.welcome.subtitle": "तुमचा शेतीचा प्रश्न कसा विचारायचा ते निवडा",
    "chat.welcome.voice": "बोला",
    "chat.welcome.voiceDesc": "रेकॉर्ड करण्यासाठी दाबा",
    "chat.welcome.type": "टाइप करा",
    "chat.welcome.typeDesc": "कीबोर्ड वापरा",
    "chat.welcome.examples": "याबद्दल विचारा:",
    "chat.thinking": "विचार करत आहे...",
    "chat.stopListening": "रेकॉर्डिंग थांबवा",
    "chat.typeQuestion": "तुमचा प्रश्न टाइप करा",

    // Common
    "common.selectLanguage": "भाषा निवडा",
    "common.loading": "लोड होत आहे...",
    "common.error": "काहीतरी चूक झाली",
    "common.retry": "पुन्हा प्रयत्न करा",
    "common.cancel": "रद्द करा",

    // Landing page
    "landing.hero.title": "आधुनिक शेतकऱ्यांसाठी AI-चालित सहाय्यक",
    "landing.hero.subtitle": "तुमच्या मातृभाषेत शेतीच्या प्रश्नांची तत्काळ उत्तरे मिळवा",
    "landing.hero.getStarted": "सुरुवात करा",
    "landing.hero.learnMore": "अधिक जाणून घ्या",

    "landing.features.title": "फार्मएजेंट का निवडावे?",
    "landing.features.subtitle": "बुद्धिमान तंत्रज्ञानासह शेतकऱ्यांना सक्षम करणे",
    "landing.features.chat.title": "स्मार्ट चॅट सहाय्यक",
    "landing.features.chat.description": "पिके, हवामान, रोगांबद्दल प्रश्न विचारा आणि तत्काळ तज्ञांचा सल्ला घ्या",
    "landing.features.voice.title": "आवाज इनपुट",
    "landing.features.voice.description": "तुमच्या भाषेत नैसर्गिकपणे बोला - टाइप करण्याची गरज नाही",
    "landing.features.multilingual.title": "बहुभाषिक समर्थन",
    "landing.features.multilingual.description": "इंग्रजी, हिंदी, कन्नड आणि मराठीमध्ये उपलब्ध",

    "landing.benefits.title": "शेतकऱ्यांसाठी फायदे",
    "landing.benefits.expert.title": "तज्ञ ज्ञान",
    "landing.benefits.expert.description": "कधीही, कुठेही कृषी तज्ञतेचा प्रवेश",
    "landing.benefits.available.title": "24/7 उपलब्ध",
    "landing.benefits.available.description": "तुम्हाला जेव्हा गरज असेल, दिवस किंवा रात्र, मदत मिळवा",
    "landing.benefits.personalized.title": "वैयक्तिक सल्ला",
    "landing.benefits.personalized.description": "तुमचे स्थान आणि पिकांवर आधारित शिफारसी",
    "landing.benefits.farmers": "10,000+",
    "landing.benefits.helping": "शेतकरी आधीच फार्मएजेंट वापरत आहेत",

    "landing.cta.title": "तुमची शेती बदलण्यासाठी तयार आहात?",
    "landing.cta.subtitle": "AI-चालित सहाय्याचा आधीच फायदा घेत असलेल्या हजारो शेतकऱ्यांमध्ये सामील व्हा",
    "landing.cta.button": "तुमचा प्रवास सुरू करा",

    // Nav
    "nav.dashboard": "डॅशबोर्ड",
    "nav.settings": "सेटिंग्ज",
    "nav.help": "मदत",
    "nav.logout": "लॉगआउट",
  },
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguage] = useState<Language>("en")

  useEffect(() => {
    const savedLanguage = localStorage.getItem("language") as Language
    if (savedLanguage && ["en", "hi", "kn", "mr"].includes(savedLanguage)) {
      setLanguage(savedLanguage)
    }
  }, [])

  const handleSetLanguage = (lang: Language) => {
    setLanguage(lang)
    localStorage.setItem("language", lang)
  }

  const t = (key: string): string => {
    return translations[language][key as keyof (typeof translations)[typeof language]] || key
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage: handleSetLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export function useLanguage() {
  const context = useContext(LanguageContext)
  if (context === undefined) {
    throw new Error("useLanguage must be used within a LanguageProvider")
  }
  return context
}
