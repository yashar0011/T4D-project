from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
from .watcher_runner import start_background_thread

app = FastAPI(title="T4D AMTS API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.on_event("startup")
async def startup():
    start_background_thread()