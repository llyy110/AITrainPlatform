import json
import traceback
import uuid
from pathlib import Path
from dotenv import load_dotenv

from .services.agent import ask_with_timeout
from .database import get_db
from .dependencies import get_current_user

# 获取项目根目录（orderPlatform 文件夹）
BASE_DIR = Path(__file__).resolve().parent.parent.parent
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path)

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .config import DATABASE_URL
from .models import Base, TrainingRecord
from .routers import files, training, records
from pydantic import BaseModel
from .services.progress_tracker import redis_client  # 复用已有 Redis 客户端

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)

app.include_router(files.router)
app.include_router(training.router)
app.include_router(records.router)


# 请求状态存储前缀
CHAT_REQUEST_PREFIX = "chat_request:"
class ChatRequest(BaseModel):
    query: str


@app.post("/train/agent/chat")
async def chat(
        req: ChatRequest,
        background_tasks: BackgroundTasks,
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # 并发控制：同一用户同时只能有一个进行中的请求
    lock_key = f"chat_lock:{current_user['id']}"
    if redis_client.exists(lock_key):
        return {"status": "processing", "message": "上一个问题正在处理中，请稍候..."}

    request_id = str(uuid.uuid4())
    redis_client.setex(lock_key, 30, request_id)  # 30秒锁，防止死锁

    # 获取当前训练任务ID（如有）
    latest_task = db.query(TrainingRecord).filter(
        TrainingRecord.user_id == current_user["id"],
        TrainingRecord.status.in_(["pending", "training"])
    ).order_by(TrainingRecord.id.desc()).first()
    task_id = latest_task.task_id if latest_task else None

    # 初始化请求状态为 "processing"
    redis_client.setex(
        f"{CHAT_REQUEST_PREFIX}{request_id}",
        60,
        '{"status": "processing"}'
    )

    def process_chat():
        try:
            answer = ask_with_timeout(
                req.query,
                user_id=str(current_user["id"]),
                current_task_id=task_id,
                timeout=15
            )
            redis_client.setex(
                f"{CHAT_REQUEST_PREFIX}{request_id}",
                60,
                f'{{"status": "completed", "answer": {json.dumps(answer)}}}'
            )
        except Exception as e:
            redis_client.setex(
                f"{CHAT_REQUEST_PREFIX}{request_id}",
                60,
                f'{{"status": "failed", "error": "处理失败"}}'
            )
        finally:
            redis_client.delete(lock_key)  # 释放锁

    background_tasks.add_task(process_chat)
    return {"request_id": request_id, "status": "processing"}

@app.get("/train/agent/chat/result/{request_id}")
async def get_chat_result(request_id: str):
    """轮询获取聊天结果"""
    key = f"{CHAT_REQUEST_PREFIX}{request_id}"
    data = redis_client.get(key)
    if not data:
        raise HTTPException(404, "请求不存在或已过期")
    import json
    result = json.loads(data)
    return result

@app.get("/train/health")
def health():
    return {"status": "ok"}







