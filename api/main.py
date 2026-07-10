import mimetypes

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from api.routers import pdf, verdict

# StaticFiles guesses MIME via the stdlib map, which doesn't know .woff2 on all
# platforms (falls back to text/plain). Register it so self-hosted fonts serve
# with the correct Content-Type.
mimetypes.add_type("font/woff2", ".woff2")

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
app.include_router(pdf.router, prefix="/api")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
