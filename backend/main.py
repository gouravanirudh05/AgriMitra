from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.database import init_db
from app.routers import auth, chat, users
from agent import orchestrator  # ✅ so we can initialize agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    await init_db()
    await orchestrator.init_orchestrator()  # ✅ Build agent before first request
    yield
    # Shutdown logic
    pass

# Initialize FastAPI app
app = FastAPI(
    title="Farmer Agent API",
    version="1.0.0",
    description="AI-powered assistant for farmers",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(chat.router, prefix="/api", tags=["chat"])

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Farmer Agent API is running"}
@app.on_event("startup")
async def startup_event():
    print("🚀 Starting AI Agent API...")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
