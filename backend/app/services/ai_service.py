import google.generativeai as genai
import os
from typing import Dict

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-pro')
else:
    model = None

class AIService:
    @staticmethod
    def get_farming_context(user_data: Dict, language: str) -> str:
        """Create context for AI based on user data and language"""
        context = f"""
        You are an AI assistant helping farmers with agricultural questions.
        You are an expert in farming, agriculture, crop management, pest control, 
        weather patterns, soil health, irrigation, and sustainable farming practices.
        
        User details:
        - Name: {user_data.get('name', 'Farmer')}
        - Location: {user_data.get('district', '')}, {user_data.get('state', '')}
        - Age: {user_data.get('age', 'Not specified')}
        - Language: {language}
        
        Guidelines:
        1. Provide helpful, practical, and actionable advice for farming questions
        2. Consider the user's location when giving advice about crops, weather, etc.
        3. Respond in the language: {language}
        4. If you don't know something specific, recommend consulting local agricultural experts
        5. Keep responses concise but informative
        6. Focus on sustainable and modern farming practices
        7. Be encouraging and supportive
        
        Language codes:
        - en: English
        - hi: Hindi (हिंदी में जवाब दें)
        - kn: Kannada (ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸಿ)
        - mr: Marathi (मराठीत उत्तर द्या)
        """
        return context
    
    @staticmethod
    async def get_ai_response(message: str, user_data: Dict, language: str) -> str:
        """Get AI response for farming question"""
        if not model:
            return AIService.get_fallback_response(language)
        
        try:
            context = AIService.get_farming_context(user_data, language)
            full_prompt = f"{context}\n\nUser question: {message}"
            
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            print(f"AI service error: {e}")
            return AIService.get_fallback_response(language)
    
    @staticmethod
    def get_fallback_response(language: str) -> str:
        """Get fallback response when AI service is unavailable"""
        fallback_responses = {
            "en": "Thank you for your farming question. For the best advice tailored to your specific situation, I recommend consulting with local agricultural experts or extension officers who can provide guidance based on your region's conditions.",
            "hi": "आपके खेती के सवाल के लिए धन्यवाद। आपकी विशिष्ट स्थिति के लिए सबसे अच्छी सलाह के लिए, मैं स्थानीय कृषि विशेषज्ञों या विस्तार अधिकारियों से सलाह लेने की सिफारिश करता हूं जो आपके क्षेत्र की स्थितियों के आधार पर मार्गदर्शन प्रदान कर सकते हैं।",
            "kn": "ನಿಮ್ಮ ಕೃಷಿ ಪ್ರಶ್ನೆಗೆ ಧನ್ಯವಾದಗಳು। ನಿಮ್ಮ ನಿರ್ದಿಷ್ಟ ಪರಿಸ್ಥಿತಿಗೆ ಅನುಗುಣವಾದ ಅತ್ಯುತ್ತಮ ಸಲಹೆಗಾಗಿ, ನಿಮ್ಮ ಪ್ರದೇಶದ ಪರಿಸ್ಥಿತಿಗಳ ಆಧಾರದ ಮೇಲೆ ಮಾರ್ಗದರ್ಶನ ನೀಡಬಲ್ಲ ಸ್ಥಳೀಯ ಕೃಷಿ ತಜ್ಞರು ಅಥವಾ ವಿಸ್ತರಣಾ ಅಧಿಕಾರಿಗಳೊಂದಿಗೆ ಸಮಾಲೋಚಿಸಲು ನಾನು ಶಿಫಾರಸು ಮಾಡುತ್ತೇನೆ।",
            "mr": "तुमच्या शेतीच्या प्रश्नासाठी धन्यवाद। तुमच्या विशिष्ट परिस्थितीसाठी सर्वोत्तम सल्ल्यासाठी, मी स्थानिक कृषी तज्ञ किंवा विस्तार अधिकाऱ्यांशी सल्लामसलत करण्याची शिफारस करतो जे तुमच्या प्रदेशाच्या परिस्थितीनुसार मार्गदर्शन देऊ शकतात।"
        }
        return fallback_responses.get(language, fallback_responses["en"])
