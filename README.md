# 🌾 Agricultural AI Assistant with LangGraph Supervisor

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-latest-green.svg)](https://github.com/langchain-ai/langgraph)
[![Gemini AI](https://img.shields.io/badge/Gemini-2.0--flash-orange.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

> An intelligent, multi-agent agricultural assistant powered by Google's Gemini AI and LangGraph supervisor pattern, designed specifically for Indian farmers and agricultural professionals. Built with government data sources and zero external API dependencies except Google's Gemini.

## 📋 Table of Contents

- [🎯 Overview](#-overview)
- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [🚀 Quick Start](#-quick-start)
- [📊 Data Sources](#-data-sources)
- [🔧 Configuration](#-configuration)
- [📖 API Documentation](#-api-documentation)
- [🧪 Testing](#-testing)
- [🚀 Deployment](#-deployment)
- [🤝 Contributing](#-contributing)
- [📞 Support](#-support)

## 🎯 Overview

The Agricultural AI Assistant is a sophisticated, production-ready system that provides comprehensive agricultural guidance through specialized AI agents. Built specifically for the Indian agricultural ecosystem, it leverages government data sources and intelligent routing to deliver accurate, contextual assistance to farmers and agricultural professionals.

### 🌟 Key Highlights

- **🇮🇳 India-First Design**: Built with Indian government data sources (IMD, AgMarkNet, Soil Health Cards)
- **🧠 Intelligent Routing**: Gemini-powered query classification and agent selection
- **🔄 Multi-Agent Architecture**: Specialized agents for different agricultural domains
- **📱 Production Ready**: Full-stack solution with React frontend and FastAPI backend
- **🆓 Cost Effective**: Only requires Google API key, all other data from free government sources
- **⚡ High Performance**: Asynchronous processing with conversation memory

## ✨ Features

### 🎯 Core Capabilities

| Feature | Description | Status |
|---------|-------------|--------|
| **🌤️ Weather Intelligence** | Real-time weather data from IMD with 7-day forecasts | ✅ Active |
| **📈 Market Analytics** | Live commodity prices from AgMarkNet across all Indian markets | ✅ Active |
| **🌱 Smart Fertilizer Recommendations** | Personalized suggestions based on Soil Health Card data | ✅ Active |
| **🔍 Plant Disease Detection** | AI-powered image analysis for crop health assessment | ✅ Active |
| **📚 Knowledge Management** | RAG system with government policies and agricultural best practices | ✅ Active |
| **🎥 Educational Content** | Curated video recommendations for agricultural learning | ✅ Active |
| **💬 Contextual Conversations** | Memory-enabled chat with user profile awareness | ✅ Active |
| **🌐 Multi-Language Support** | Hindi and English language support | 🔄 In Progress |

### 🤖 Specialized Agents

<details>
<summary><b>🌤️ Weather Agent</b></summary>

**Data Source**: India Meteorological Department (IMD)
- Current weather conditions for any Indian location
- 7-day detailed weather forecasts
- Agricultural weather advisories
- Rainfall patterns and seasonal predictions
- Extreme weather alerts for crop protection

**Capabilities**:
- District-level weather data
- Crop-specific weather recommendations
- Irrigation scheduling based on rainfall forecasts
- Pest and disease risk assessment based on weather patterns
</details>

<details>
<summary><b>📈 Market Agent</b></summary>

**Data Source**: AgMarkNet (Government Agricultural Marketing)
- Real-time commodity prices across 8,000+ markets
- Price trend analysis and predictions
- Market comparisons for better selling decisions
- Seasonal price patterns
- Transportation and storage cost optimization

**Capabilities**:
- State-wise and market-wise price comparisons
- Best selling time recommendations
- Price alerts for target commodities
- Market demand forecasting
</details>

<details>
<summary><b>🌱 Fertilizer Agent</b></summary>

**Data Source**: Soil Health Card Database
- Personalized fertilizer recommendations
- Soil nutrient analysis interpretation
- Organic vs chemical fertilizer guidance
- Cost-effective fertilizer combinations
- Application timing and dosage recommendations

**Capabilities**:
- Soil test report analysis
- Crop-specific nutrient requirements
- Budget-friendly fertilizer alternatives
- Micronutrient deficiency solutions
</details>

<details>
<summary><b>🔍 Image Agent</b></summary>

**Technology**: Custom-trained models on Indian crop diseases
- Plant disease identification from photos
- Pest detection and classification
- Crop health assessment
- Growth stage identification
- Deficiency symptom analysis

**Capabilities**:
- Support for 50+ common Indian crops
- Detection of 200+ diseases and pests
- Treatment recommendations with local solutions
- Severity assessment and spread prediction

<summary><b>📚 Knowledge Agent</b></summary>

**Data Sources**: 
- Government agricultural magazines and publications
- Policy documents and scheme information
- KCC (Kisan Call Center) historical queries
- Research papers from Indian agricultural institutes

**Capabilities**:
- Government scheme eligibility and application process
- Best practices for crop cultivation
- Organic farming techniques
- Post-harvest management
- Financial assistance and subsidy information
</details>

<details>
<summary><b>🎥 YouTube Agent</b></summary>

**Technology**: Intelligent web scraping and content curation
- Educational video recommendations
- Practical farming demonstrations
- Expert interviews and talks
- Crop-specific tutorials
- Modern farming technology showcases

**Capabilities**:
- Content filtering for quality and relevance
- Language-based recommendations
- Trending agricultural topics
- Expert channel prioritization
</details>

## 🏗️ Architecture

### System Architecture Diagram

```mermaid
graph TB
   subgraph "User Interface Layer"
       UI[React Frontend]
       API[FastAPI Backend]
   end
   
   subgraph "Orchestration Layer"
       SUPER[LangGraph Supervisor]
       GEMINI[Gemini Router]
   end
   
   subgraph "Agent Layer"
       WA[Weather Agent]
       MA[Market Agent]
       FA[Fertilizer Agent]
       IA[Image Agent]
       KA[Knowledge Agent]
       YA[YouTube Agent]
   end
   
   subgraph "Data Layer"
       IMD[(IMD Weather Data)]
       AGM[(AgMarkNet Prices)]
       SHC[(Soil Health Cards)]
       GOV[(Government Documents)]
       YT[(YouTube Content)]
       ML[(ML Models)]
   end
   
   UI --> API
   API --> SUPER
   SUPER --> GEMINI
   GEMINI --> WA
   GEMINI --> MA
   GEMINI --> FA
   GEMINI --> IA
   GEMINI --> KA
   GEMINI --> YA
   
   WA --> IMD
   MA --> AGM
   FA --> SHC
   IA --> ML
   KA --> GOV
   YA --> YT
