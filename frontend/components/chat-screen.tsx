"use client"

import { useState, useRef, useEffect } from "react"
import { useAuth } from "@/contexts/auth-context"
import { useLanguage } from "@/contexts/language-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useToast } from "@/hooks/use-toast"
import {
  Send,
  Mic,
  MicOff,
  MessageSquare,
  Plus,
  Menu,
  LogOut,
  User,
  Keyboard,
  Wheat,
  Bug,
  CloudRain,
  Sprout,
  Home,
  History,
  Settings,
  HelpCircle,
} from "lucide-react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import LanguageSelector from "./language-selector"
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Message {
  id: string
  text: string
  isUser: boolean
  timestamp: Date
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
}

export default function ChatScreen() {
  const [message, setMessage] = useState("")
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null)
  const [isListening, setIsListening] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [showTextInput, setShowTextInput] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)

  const { user, logout } = useAuth()
  const { t, language } = useLanguage()
  const { toast } = useToast()

  const recognitionRef = useRef<any>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationFrameRef = useRef<number>()
  const mediaStreamRef = useRef<MediaStream | null>(null)

  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  // Example questions based on language
  const getExampleQuestions = () => {
    const examples = {
      en: [
        { icon: Wheat, text: "What's the best time to plant rice?", category: "Crops" },
        { icon: Bug, text: "How to control pests in tomatoes?", category: "Pest Control" },
        { icon: CloudRain, text: "When should I water my crops?", category: "Irrigation" },
        { icon: Sprout, text: "Which fertilizer is best for wheat?", category: "Fertilizers" },
      ],
      hi: [
        { icon: Wheat, text: "चावल बोने का सबसे अच्छा समय क्या है?", category: "फसल" },
        { icon: Bug, text: "टमाटर में कीड़ों को कैसे नियंत्रित करें?", category: "कीट नियंत्रण" },
        { icon: CloudRain, text: "मुझे अपनी फसलों को कब पानी देना चाहिए?", category: "सिंचाई" },
        { icon: Sprout, text: "गेहूं के लिए कौन सा उर्वरक सबसे अच्छा है?", category: "उर्वरक" },
      ],
      kn: [
        { icon: Wheat, text: "ಅಕ್ಕಿ ಬೀಜ ಬಿತ್ತಲು ಉತ್ತಮ ಸಮಯ ಯಾವುದು?", category: "ಬೆಳೆಗಳು" },
        { icon: Bug, text: "ಟೊಮೇಟೊದಲ್ಲಿ ಕೀಟಗಳನ್ನು ಹೇಗೆ ನಿಯಂತ್ರಿಸುವುದು?", category: "ಕೀಟ ನಿಯಂತ್ರಣ" },
        { icon: CloudRain, text: "ನನ್ನ ಬೆಳೆಗಳಿಗೆ ಯಾವಾಗ ನೀರು ಹಾಕಬೇಕು?", category: "ನೀರಾವರಿ" },
        { icon: Sprout, text: "ಗೋಧಿಗೆ ಯಾವ ರಸಗೊಬ್ಬರ ಉತ್ತಮ?", category: "ರಸಗೊಬ್ಬರಗಳು" },
      ],
      mr: [
        { icon: Wheat, text: "तांदूळ लावण्याची सर्वोत्तम वेळ कोणती?", category: "पिके" },
        { icon: Bug, text: "टोमॅटोमध्ये कीड कसे नियंत्रित करावे?", category: "कीड नियंत्रण" },
        { icon: CloudRain, text: "माझ्या पिकांना कधी पाणी द्यावे?", category: "सिंचन" },
        { icon: Sprout, text: "गहूसाठी कोणते खत सर्वोत्तम आहे?", category: "खते" },
      ],
    }
    return examples[language as keyof typeof examples] || examples.en
  }

  useEffect(() => {
    // Initialize speech recognition with better browser support detection
    if (typeof window !== 'undefined') {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition()
        recognitionRef.current.continuous = true // Changed to false for better control
        recognitionRef.current.interimResults = true
        recognitionRef.current.lang = getLanguageCode(language)
        recognitionRef.current.maxAlternatives = 1

        recognitionRef.current.onstart = () => {
          console.log('Speech recognition started')
        }
        let silenceTimeout: NodeJS.Timeout
        let finalTranscript = ""
        recognitionRef.current.onresult = (event: any) => {
          clearTimeout(silenceTimeout) // Reset the silence timeout
              silenceTimeout = setTimeout(() => {
              recognitionRef.current?.stop()
          }, 5000)
          let interimTranscript = ""
          
          
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript
            if (event.results[i].isFinal) {
              finalTranscript += transcript
            } else {
              interimTranscript += transcript
            }
          }
          
          // Update the input field with live transcription
          const currentText = interimTranscript || finalTranscript
          if (currentText) {
            setMessage(currentText.trim())
          }
        }

        recognitionRef.current.onerror = (event: any) => {
          console.error("Speech recognition error:", event.error)
          setIsListening(false)
          stopAudioVisualization()
          
          if (event.error !== 'aborted') {
            toast({
              title: t("common.error"),
              description: "Voice recognition failed. Please try again.",
              variant: "destructive",
            })
          }
        }

        recognitionRef.current.onend = () => {
          console.log('Speech recognition ended')
          finalTranscript = ""
          setIsListening(false)
          stopAudioVisualization()
        }
      }
    }

    // Cleanup on unmount
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
      stopAudioVisualization()
    }
  }, [language, t, toast])

  useEffect(() => {
    scrollToBottom()
  }, [currentConversation?.messages])

  // Load conversations from backend
  useEffect(() => {
    const loadConversations = async () => {
      if (user?.id) {
        try {
          const response = await fetch(`${API_BASE_URL}/api/conversations/${user.id}`)
          if (response.ok) {
            const data = await response.json()
            const formattedConversations = data.map((conv: any) => ({
              ...conv,
              createdAt: new Date(conv.createdAt),
              messages: conv.messages.map((msg: any) => ({
                ...msg,
                timestamp: new Date(msg.timestamp),
              })),
            }))
            setConversations(formattedConversations)
          }
        } catch (error) {
          console.error("Failed to load conversations:", error)
        }
      }
    }

    loadConversations()
  }, [user?.id, API_BASE_URL])

  const getLanguageCode = (lang: string) => {
    const langMap: { [key: string]: string } = {
      en: "en-US",
      hi: "hi-IN",
      kn: "kn-IN",
      mr: "mr-IN",
    }
    return langMap[lang] || "en-US"
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const startAudioVisualization = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      mediaStreamRef.current = stream
      audioContextRef.current = new AudioContext()
      analyserRef.current = audioContextRef.current.createAnalyser()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)

      analyserRef.current.fftSize = 256
      const bufferLength = analyserRef.current.frequencyBinCount
      const dataArray = new Uint8Array(bufferLength)

      const updateAudioLevel = () => {
        if (analyserRef.current && isListening) {
          analyserRef.current.getByteFrequencyData(dataArray)
          const average = dataArray.reduce((a, b) => a + b) / bufferLength
          setAudioLevel(average / 255)
          animationFrameRef.current = requestAnimationFrame(updateAudioLevel)
        }
      }
      updateAudioLevel()
    } catch (error) {
      console.error("Error accessing microphone:", error)
      toast({
        title: t("common.error"),
        description: "Microphone access denied or not available.",
        variant: "destructive",
      })
      setIsListening(false)
    }
  }

  const stopAudioVisualization = () => {
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current)
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = null
    }
    setAudioLevel(0)
  }

  const startListening = () => {
    if (!recognitionRef.current) {
      toast({
        title: t("common.error"),
        description: "Speech recognition is not supported in your browser.",
        variant: "destructive",
      })
      return
    }

    if (!isListening) {
      setMessage("")
      setIsListening(true)
      recognitionRef.current.lang = getLanguageCode(language)
      
      try {
        recognitionRef.current.start()
        startAudioVisualization()
        setShowTextInput(true)
      } catch (error) {
        console.error('Error starting speech recognition:', error)
        setIsListening(false)
        toast({
          title: t("common.error"),
          description: "Failed to start voice recognition.",
          variant: "destructive",
        })
      }
    }
  }

  const stopListening = () => {
    if (recognitionRef.current && isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
      stopAudioVisualization()
    }
  }

  const sendMessage = async (messageText?: string) => {
    const textToSend = messageText || message
    if (!textToSend.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      text: textToSend,
      isUser: true,
      timestamp: new Date(),
    }

    let conversation = currentConversation
    if (!conversation) {
      conversation = {
        id: Date.now().toString(),
        title: textToSend.slice(0, 50) + (textToSend.length > 50 ? "..." : ""),
        messages: [],
        createdAt: new Date(),
      }
      setCurrentConversation(conversation)
    }

    const updatedConversation = {
      ...conversation,
      messages: [...conversation.messages, userMessage],
    }
    setCurrentConversation(updatedConversation)
    setMessage("")
    setShowTextInput(false)
    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: textToSend,
          language: language,
          userId: user?.id,
          conversationId: conversation.id,
        }),
      })

      if (response.ok) {
        const data = await response.json()
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          text: data.response,
          isUser: false,
          timestamp: new Date(),
        }

        const finalConversation = {
          ...updatedConversation,
          messages: [...updatedConversation.messages, botMessage],
        }

        setCurrentConversation(finalConversation)

        const updatedConversations = conversations.filter((c) => c.id !== conversation.id)
        updatedConversations.unshift(finalConversation)
        setConversations(updatedConversations)
      } else {
        throw new Error("Failed to send message")
      }
    } catch (error) {
      toast({
        title: t("common.error"),
        description: "Failed to send message. Please try again.",
        variant: "destructive",
      })
    } finally {
      setIsLoading(false)
    }
  }

  const startNewChat = () => {
    setCurrentConversation(null)
    setMessage("")
    setShowTextInput(false)
    setIsListening(false)
    stopAudioVisualization()
    if (recognitionRef.current) {
      recognitionRef.current.stop()
    }
  }

  const selectConversation = (conversation: Conversation) => {
    setCurrentConversation(conversation)
    setShowTextInput(false)
    setIsListening(false)
    stopAudioVisualization()
    if (recognitionRef.current) {
      recognitionRef.current.stop()
    }
  }

  const handleExampleQuestion = (question: string) => {
    setMessage(question)
    sendMessage(question)
  }

  // New Chat Welcome Screen
  const renderWelcomeScreen = () => (
    <div className="flex-1 flex flex-col items-center justify-center p-8 space-y-8">
      <div className="text-center space-y-4">
        <div className="p-4 bg-green-100 rounded-full w-fit mx-auto">
          <MessageSquare className="h-12 w-12 text-green-600" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900">{t("chat.welcome.title")}</h2>
        <p className="text-gray-600 max-w-md">{t("chat.welcome.subtitle")}</p>
      </div>

      {/* Voice and Text Input Options */}
      <div className="flex flex-col sm:flex-row gap-6">
        {/* Voice Input */}
        <div className="flex flex-col items-center space-y-4">
          <Button
            size="lg"
            className={`w-24 h-24 rounded-full transition-all duration-200 ${
              isListening 
                ? "bg-red-500 hover:bg-red-600 animate-pulse shadow-lg" 
                : "bg-green-600 hover:bg-green-700 shadow-md hover:shadow-lg"
            }`}
            onClick={isListening ? stopListening : startListening}
          >
            {isListening ? (
              <div className="flex flex-col items-center">
                <MicOff className="h-8 w-8" />
                <div
                  className="w-2 h-2 bg-white rounded-full mt-1 transition-all duration-100"
                  style={{
                    transform: `scale(${1 + audioLevel * 2})`,
                    opacity: 0.7 + audioLevel * 0.3,
                  }}
                />
              </div>
            ) : (
              <Mic className="h-8 w-8" />
            )}
          </Button>
          <div className="text-center">
            <p className="font-medium text-gray-900">{t("chat.welcome.voice")}</p>
            <p className="text-sm text-gray-500">{t("chat.welcome.voiceDesc")}</p>
          </div>
        </div>

        {/* Text Input */}
        <div className="flex flex-col items-center space-y-4">
          <Button
            size="lg"
            variant="outline"
            className="w-24 h-24 rounded-full border-2 border-green-600 text-green-600 hover:bg-green-50 bg-transparent shadow-md hover:shadow-lg transition-all duration-200"
            onClick={() => {
              setShowTextInput(true)
              stopListening()
            }}
          >
            <Keyboard className="h-8 w-8" />
          </Button>
          <div className="text-center">
            <p className="font-medium text-gray-900">{t("chat.welcome.type")}</p>
            <p className="text-sm text-gray-500">{t("chat.welcome.typeDesc")}</p>
          </div>
        </div>
      </div>
<LanguageSelector />
      {/* Text Input Field (shown below buttons) */}
      {showTextInput && (
        <div className="w-full max-w-2xl space-y-4">
          <Input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={t("chat.placeholder")}
            className="h-12 text-base"
            onKeyPress={(e) => e.key === "Enter" && sendMessage()}
            autoFocus={!isListening}
          />
          <Button
            onClick={() => sendMessage()}
            disabled={!message.trim() || isLoading}
            className="w-full h-12 text-base"
          >
            <Send className="h-5 w-5 mr-2" />
            {t("chat.send")}
          </Button>
          {isListening && (
            <div className="text-center mt-2 p-3 bg-green-50 rounded-lg border border-green-200">
              <p className="text-sm text-green-600 font-medium">{t("chat.listening")}</p>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={stopListening} 
                className="mt-2 bg-white hover:bg-gray-50"
              >
                {t("chat.stopRecording")}
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Example Questions */}
      {!showTextInput && (
        <div className="w-full max-w-2xl space-y-4">
          <h3 className="text-lg font-semibold text-center text-gray-900">{t("chat.welcome.examples")}</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {getExampleQuestions().map((example, index) => (
              <Button
                key={index}
                variant="outline"
                className="h-auto p-4 text-left justify-start hover:bg-green-50 hover:border-green-300 bg-transparent transition-colors duration-200"
                onClick={() => handleExampleQuestion(example.text)}
              >
                <div className="flex items-start space-x-3">
                  <div className="p-2 bg-green-100 rounded-lg">
                    <example.icon className="h-5 w-5 text-green-600" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">{example.text}</p>
                    <p className="text-xs text-gray-500">{example.category}</p>
                  </div>
                </div>
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  )

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Fixed Header */}
      <div className="flex items-center justify-between p-4 bg-white border-b shadow-sm sticky top-0 z-10">
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="sm" className="p-2">
              <Menu className="h-5 w-5" />
              <span className="sr-only">Open menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-80">
            <SheetHeader>
              <SheetTitle className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-full">
                  <User className="h-5 w-5 text-green-600" />
                </div>
                <div className="text-left">
                  <p className="font-semibold">{user?.name || "Farmer"}</p>
                  <p className="text-sm text-gray-500">
                    {user?.state}, {user?.district}
                  </p>
                </div>
              </SheetTitle>
            </SheetHeader>

            <div className="mt-6 space-y-6">
              {/* Quick Actions */}
              <div className="space-y-3">
                <Button onClick={startNewChat} className="w-full justify-start h-12">
                  <Plus className="h-5 w-5 mr-3" />
                  {t("chat.newChat")}
                </Button>

                <Button variant="outline" className="w-full justify-start h-12 bg-transparent">
                  <Home className="h-5 w-5 mr-3" />
                  {t("nav.dashboard")}
                </Button>
              </div>

              {/* Conversations */}
              <div>
                <div className="flex items-center gap-2 mb-3">
                  <History className="h-4 w-4 text-gray-500" />
                  <h3 className="font-medium text-gray-900">{t("chat.conversations")}</h3>
                </div>
                <ScrollArea className="h-60">
                  <div className="space-y-2">
                    {conversations.map((conv) => (
                      <Button
                        key={conv.id}
                        variant={currentConversation?.id === conv.id ? "secondary" : "ghost"}
                        className="w-full justify-start text-left h-auto p-3"
                        onClick={() => selectConversation(conv)}
                      >
                        <MessageSquare className="h-4 w-4 mr-3 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="font-medium truncate text-sm">{conv.title}</div>
                          <div className="text-xs text-muted-foreground">{conv.createdAt.toLocaleDateString()}</div>
                        </div>
                      </Button>
                    ))}
                  </div>
                </ScrollArea>
              </div>

              {/* Settings & Language */}
              <div className="pt-4 border-t space-y-3">
                <div className="flex items-center gap-2 mb-2">
                  <Settings className="h-4 w-4 text-gray-500" />
                  <span className="text-sm font-medium text-gray-900">{t("nav.settings")}</span>
                </div>
                <Button variant="ghost" className="w-full justify-start h-10">
                  <HelpCircle className="h-4 w-4 mr-3" />
                  {t("nav.help")}
                </Button>
                <Button variant="ghost" onClick={logout} className="w-full justify-start text-red-600 h-10">
                  <LogOut className="h-4 w-4 mr-3" />
                  {t("nav.logout")}
                </Button>
              </div>
            </div>
          </SheetContent>
        </Sheet>

        <div className="flex items-center gap-2">
          <div className="p-2 bg-green-100 rounded-lg">
            <Sprout className="h-5 w-5 text-green-600" />
          </div>
          <h1 className="text-lg font-semibold text-green-800">{t("chat.title")}</h1>
        </div>

        <div className="w-10" />
      </div>

      {/* Chat Content */}
      {!currentConversation ? (
        renderWelcomeScreen()
      ) : (
        <>
          {/* Messages */}
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4 max-w-2xl mx-auto">
              {currentConversation.messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.isUser ? "justify-end" : "justify-start"}`}>
                  <Card className={`max-w-[80%] ${msg.isUser ? "bg-green-600 text-white" : "bg-white border"}`}>
                    <CardContent className="p-3">
                      <p className="text-sm"><Markdown remarkPlugins={[remarkGfm]}>{msg.text}</Markdown></p>
                      <p className={`text-xs mt-1 ${msg.isUser ? "text-green-100" : "text-gray-500"}`}>
                        {msg.timestamp.toLocaleTimeString()}
                      </p>
                    </CardContent>
                  </Card>
                </div>
              ))}

              {isLoading && (
                <div className="flex justify-start">
                  <Card className="bg-white border">
                    <CardContent className="p-3">
                      <div className="flex items-center space-x-2">
                        <div className="animate-pulse flex space-x-1">
                          <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                          <div className="w-2 h-2 bg-gray-400 rounded-full"></div>
                        </div>
                        <span className="text-sm text-gray-500">{t("chat.thinking")}</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Input Area */}
          <div className="p-4 bg-white border-t">
            <div className="flex items-center space-x-2 max-w-2xl mx-auto">
              <div className="flex-1 relative">
                <Input
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder={t("chat.placeholder")}
                  className="h-12 pr-12"
                  onKeyPress={(e) => e.key === "Enter" && sendMessage()}
                />
                <Button
                  type="button"
                  size="sm"
                  variant={isListening ? "destructive" : "ghost"}
                  className={`absolute right-1 top-1 h-10 w-10 ${isListening ? 'animate-pulse' : ''}`}
                  onClick={isListening ? stopListening : startListening}
                >
                  {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
                </Button>
              </div>
              <Button onClick={() => sendMessage()} disabled={!message.trim() || isLoading} className="h-12 w-12">
                <Send className="h-4 w-4" />
              </Button>
            </div>
            {isListening && (
              <div className="text-center mt-2 p-2 bg-green-50 rounded-lg border border-green-200">
                <p className="text-sm text-green-600 font-medium">{t("chat.listening")}</p>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={stopListening} 
                  className="mt-1 bg-white hover:bg-gray-50"
                >
                  {t("chat.stopRecording")}
                </Button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}