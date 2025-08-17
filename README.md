# AgriMitra (AI Assistant with LangGraph Supervisor)

An intelligent agricultural assistant powered by Google's Gemini AI and LangGraph supervisor pattern, featuring specialized agents for weather, market data, plant disease detection, fertilizer recommendations, and agricultural knowledge management.

## 🏗️ Architecture

```mermaid
graph TD
   A[User Query] --> B[LangGraph Supervisor]
   B --> C[Gemini Router]

   C --> D[Weather Agent]
   C --> E[Market Agent]
   C --> F[Fertilizer Agent]
   C --> G[Image Agent]
   C --> H[Knowledge Agent]
   C --> I[YouTube Agent]

   D --> J[Weather APIs]
   E --> K[Market Data]
   F --> L[Fertilizer DB]
   G --> M[Plant Disease Models]
   H --> N[Knowledge Base/RAG]
   I --> O[YouTube API]

   D --> P[Supervisor Response]
   E --> P
   F --> P
   G --> P
   H --> P
   I --> P
