import os
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from graph.workflow import workflow
from utils.logger import configure_logging
from config import Settings

app = FastAPI(title="Email AI Agent API")

# Configure logging
settings = Settings()
logger = configure_logging(settings.log_dir)

# CORS – allow Gmail and extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "chrome-extension://oinkjmplingonmbgjhpncdlokngmjnfp",
        "https://mail.google.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EmailGenerateRequest(BaseModel):
    email_content: str
    sender: str = ""
    subject: str = ""

@app.get("/")
def read_root():
    return {"status": "online", "message": "Email AI Agent Service is running!"}

@app.post("/api/v1/generate-reply")
async def generate_reply(payload: EmailGenerateRequest):
    try:
        initial_state = {
            "email_id": "manual",
            "sender": payload.sender,
            "subject": payload.subject,
            "body": payload.email_content,
            "message_id": None,
            "sentiment": None,
            "context": None,
            "draft_reply": None,
            "reviewed_reply": None,
            "final_reply": None,
        }
        result = workflow.invoke(initial_state)
        reply = result.get("final_reply") or result.get("draft_reply", "Tidak ada balasan.")
        return {
            "success": True,
            "reply": reply,
            "sentiment": result.get("sentiment", "neutral")
        }
    except Exception as e:
        logger.error("API generate_reply error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ===== JALANKAN WORKER DI BACKGROUND THREAD =====
from main import main as worker_main

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=worker_main, daemon=True)
    thread.start()
    logger.info("Worker started in background thread.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
