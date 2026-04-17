from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timedelta

from ..dependencies import get_current_user
from ..models import TrainingRecord
from ..services.training_worker import train_bpnn_classifier, train_bpnn_regressor, train_cnn_image_classifier
from ..services.progress_tracker import get_progress, get_logs
from ..database import get_db

router = APIRouter(prefix="/train/training", tags=["training"])


class StartTrainingRequest(BaseModel):
    model_type: str
    hidden_layer_sizes: int
    max_iter: int
    learning_rate: float
    data_path: str


@router.post("/start")
async def start_training(
        req: StartTrainingRequest,
        background_tasks: BackgroundTasks,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    task_id = str(uuid.uuid4())
    # 创建记录
    record = TrainingRecord(
        user_id=current_user["id"],
        task_id=task_id,
        model_type=req.model_type,
        hidden_layer_sizes=req.hidden_layer_sizes,
        max_iter=req.max_iter,
        learning_rate=req.learning_rate,
        data_path=req.data_path,
        status="pending",
        expired_at=datetime.utcnow() + timedelta(days=365)
    )
    db.add(record)
    db.commit()

    # 异步执行训练
    if req.model_type == "train_bpnn_classifier":
        background_tasks.add_task(train_bpnn_classifier, 'hdfs://127.0.0.1:9000' + req.data_path, req.hidden_layer_sizes,
                                  req.learning_rate, req.max_iter, task_id, current_user["id"], db)
    elif req.model_type == "train_bpnn_regressor":
        background_tasks.add_task(train_bpnn_regressor, 'hdfs://127.0.0.1:9000' + req.data_path, req.hidden_layer_sizes,
                                  req.learning_rate, req.max_iter, task_id, current_user["id"], db)
    elif req.model_type == "train_cnn_img_classifier":
        background_tasks.add_task(train_cnn_image_classifier, 'hdfs://127.0.0.1:9000' + req.data_path, req.hidden_layer_sizes,
                                  req.learning_rate, req.max_iter, task_id, current_user["id"], db)
    else:
        raise HTTPException(400, "Unknown model type")

    return {"task_id": task_id, "record_id": record.id}


@router.post("/stop/{task_id}")
async def stop_training(
        task_id: str,
        current_user: dict = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    # 验证任务是否存在且属于当前用户
    record = db.query(TrainingRecord).filter(
        TrainingRecord.task_id == task_id,
        TrainingRecord.user_id == current_user["id"]
    ).first()
    if not record:
        raise HTTPException(404, "Task not found")
    if record.status not in ["pending", "training"]:
        raise HTTPException(400, "Task is not running")

    # 在 Redis 中设置停止标志
    from ..services.progress_tracker import redis_client
    redis_client.set(f"training:{task_id}:stop", "1", ex=3600)

    # 更新数据库状态
    record.status = "stopping"
    db.commit()

    return {"message": "Stop signal sent"}

@router.get("/progress/{task_id}")
async def get_training_progress(task_id: str):
    progress = get_progress(task_id)
    if not progress:
        raise HTTPException(404, "Task not found")
    return progress
@router.get("/log/{task_id}")
async def get_training_log(task_id: str, tail: int = None):
    """
    获取训练日志
    - tail: 可选，返回最后 N 行（例如 ?tail=100）
    """
    logs = get_logs(task_id, tail=tail)
    return {"logs": logs}

@router.get("/latest")
async def get_latest_training(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户最新的一条训练记录（不限状态）"""
    record = db.query(TrainingRecord).filter(
        TrainingRecord.user_id == current_user["id"]
    ).order_by(TrainingRecord.id.desc()).first()
    if not record:
        return None
    return {
        "task_id": record.task_id,
        "status": record.status,
        "created_at": record.start_time.isoformat(),
        "model_type": record.model_type,
        "data_path": record.data_path
    }

def get_train_function(model_type: str):
    """根据模型类型返回对应的训练函数"""
    if model_type == "train_bpnn_classifier":
        return train_bpnn_classifier
    elif model_type == "train_bpnn_regressor":
        return train_bpnn_regressor
    elif model_type == "train_cnn_img_classifier":
        return train_cnn_image_classifier
    else:
        raise ValueError(f"Unknown model type: {model_type}")


@router.post("/rerun/{record_id}")
async def rerun_training(
    record_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """从历史记录重新运行训练"""
    # 获取历史记录
    record = db.query(TrainingRecord).filter(
        TrainingRecord.id == record_id,
        TrainingRecord.user_id == current_user["id"]
    ).first()
    if not record:
        raise HTTPException(404, "记录不存在")

    # 复用参数
    params = {
        "model_type": record.model_type,
        "hidden_layer_sizes": record.hidden_layer_sizes,
        "max_iter": record.max_iter,
        "learning_rate": record.learning_rate,
        "data_path": record.data_path
    }

    # 生成新任务ID
    task_id = str(uuid.uuid4())

    # 创建新记录
    new_record = TrainingRecord(
        user_id=current_user["id"],
        task_id=task_id,
        model_type=params["model_type"],
        hidden_layer_sizes=params["hidden_layer_sizes"],
        max_iter=params["max_iter"],
        learning_rate=params["learning_rate"],
        data_path=params["data_path"],
        status="pending",
        expired_at=datetime.utcnow() + timedelta(days=365)
    )
    db.add(new_record)
    db.commit()

    # 异步执行训练
    train_func = get_train_function(params["model_type"])
    background_tasks.add_task(
        train_func,
        'hdfs://127.0.0.1:9000' + params["data_path"],
        params["hidden_layer_sizes"],
        params["learning_rate"],
        params["max_iter"],
        task_id,
        current_user["id"],
        db
    )

    return {"task_id": task_id, "record_id": new_record.id}













