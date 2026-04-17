from pathlib import Path
from dotenv import load_dotenv

from .database import get_db
from .dependencies import get_current_user

# 获取项目根目录（orderPlatform 文件夹）
BASE_DIR = Path(__file__).resolve().parent.parent.parent
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path)

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .config import DATABASE_URL
from .models import Base, TrainingRecord
from .routers import files, training, records
from pydantic import BaseModel
from .services.agent import ask

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)

app.include_router(files.router)
app.include_router(training.router)
app.include_router(records.router)

class ChatRequest(BaseModel):
    query: str

@app.post("/train/agent/chat")
async def chat(req: ChatRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    # 获取用户最新进行中的任务
    latest_task = db.query(TrainingRecord).filter(
        TrainingRecord.user_id == current_user["id"],
        TrainingRecord.status.in_(["pending", "training"])
    ).order_by(TrainingRecord.id.desc()).first()
    task_id = latest_task.task_id if latest_task else None
    answer = ask(req.query, user_id=current_user["id"], current_task_id=task_id)
    return {"answer": answer}

@app.get("/train/health")
def health():
    return {"status": "ok"}







