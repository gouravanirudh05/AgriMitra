from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import asyncio

from app.database import init_db
from app.routers import auth, chat, users
from agent import orchestrator


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    asyncio.create_task(orchestrator.init_orchestrator())  # ✅ Background load
    yield
    # Shutdown logic
    pass


app = FastAPI(
    title="Farmer Agent API",
    version="1.0.0",
    description="AI-powered assistant for farmers",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Farmer Agent API is running"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
