from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from api.routers import verdict

app = FastAPI(
    title="The Question Engine",
    description="Fifteen questions every specialty food CEO asks, answered with rules-based verdicts.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(verdict.router, prefix="/api")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
