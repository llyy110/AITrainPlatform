import json
import redis
from ..config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD
from sqlalchemy.orm import Session
from ..models import TrainingRecord, TrainingEpoch
from datetime import datetime

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    decode_responses=True
)


def set_phase(task_id, phase):
    redis_client.hset(f"training:{task_id}", "phase", phase)


def get_phase(task_id):
    return redis_client.hget(f"training:{task_id}", "phase")


def update_progress(task_id, epoch, error, accuracy=None, training_duration=0, data_loading_duration=0, max_epochs=0):
    key = f"training:{task_id}"
    # 将 numpy 类型转换为原生 Python 类型，避免存储 'np.float64(...)' 字符串
    error_val = float(error) if error is not None else 0.0
    acc_val = float(accuracy) if accuracy is not None else None
    training_duration_val = float(training_duration)
    data_loading_duration_val = float(data_loading_duration)

    redis_client.hset(key, "epoch", epoch)
    redis_client.hset(key, "error", error_val)
    redis_client.hset(key, "progress_percent", int((epoch / max_epochs) * 100) if max_epochs else 0)
    redis_client.hset(key, "training_duration", training_duration_val)
    redis_client.hset(key, "max_epochs", max_epochs)

    # 存储epochs列表
    epochs_key = f"training:{task_id}:epochs"
    epoch_data = {
        "epoch": epoch,
        "error": error_val,
        "accuracy": acc_val,
        "training_duration": training_duration_val,
        "data_loading_duration": data_loading_duration_val,
        "timestamp": datetime.utcnow().timestamp()
    }
    redis_client.rpush(epochs_key, json.dumps(epoch_data))
    # 设置过期时间1小时
    redis_client.expire(key, 3600)
    redis_client.expire(epochs_key, 3600)


def get_progress(task_id):
    key = f"training:{task_id}"
    data = redis_client.hgetall(key)
    if not data:
        return None
    epochs_key = f"training:{task_id}:epochs"
    epochs = [json.loads(e) for e in redis_client.lrange(epochs_key, 0, -1)]
    return {
        "phase": data.get("phase", ""),
        "epoch": int(data.get("epoch", 0)),
        "error": float(data.get("error", 0)),
        "progress_percent": int(data.get("progress_percent", 0)),
        "training_duration": float(data.get("training_duration", 0)),
        "max_epochs": int(data.get("max_epochs", 0)),
        "epochs": epochs
    }


def finalize_record(db: Session, task_id, status, final_error, final_accuracy=None, final_mae=None, model_path=None,
                    log_path=None, error_message=None):
    record = db.query(TrainingRecord).filter(TrainingRecord.task_id == task_id).first()
    if record:
        record.status = status
        record.end_time = datetime.utcnow()
        record.final_error = final_error
        record.final_accuracy = final_accuracy
        record.final_mae = final_mae
        record.model_save_path = model_path
        record.training_log_path = log_path
        if error_message:
            print(f"Task {task_id} failed: {error_message}")
        db.commit()
        # 保存epochs到数据库
        epochs_key = f"training:{task_id}:epochs"
        epochs = [json.loads(e) for e in redis_client.lrange(epochs_key, 0, -1)]
        for ep in epochs:
            epoch_obj = TrainingEpoch(
                record_id=record.id,
                epoch=ep["epoch"],
                error=ep["error"],
                accuracy=ep.get("accuracy"),
                training_duration=ep["training_duration"],
                data_loading_duration=ep.get("data_loading_duration", 0)
            )
            db.add(epoch_obj)
        db.commit()


# ---------- 日志操作 ----------
def append_log(task_id: str, line: str):
    key = f"training:{task_id}:logs"
    redis_client.rpush(key, line)
    redis_client.expire(key, 3600)


def get_logs(task_id: str, tail: int = None) -> str:
    key = f"training:{task_id}:logs"
    if tail:
        lines = redis_client.lrange(key, -tail, -1)
    else:
        lines = redis_client.lrange(key, 0, -1)
    return "\n".join(lines)


def clear_logs(task_id: str):
    key = f"training:{task_id}:logs"
    redis_client.delete(key)