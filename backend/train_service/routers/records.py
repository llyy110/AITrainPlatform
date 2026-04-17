from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime
import csv, io, json

from ..dependencies import get_current_user
from ..models import TrainingRecord, TrainingEpoch
from ..database import get_db

router = APIRouter(prefix="/train/training/records", tags=["records"])

@router.get("")
def get_records(page: int = 1, page_size: int = 20, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    offset = (page - 1) * page_size
    query = db.query(TrainingRecord).filter(TrainingRecord.user_id == current_user["id"]).order_by(desc(TrainingRecord.id))
    total = query.count()
    records = query.offset(offset).limit(page_size).all()
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "model_type": r.model_type,
            "data_path": r.data_path,
            "status": r.status,
            "final_error": r.final_error,
            "final_accuracy": r.final_accuracy,
            "created_at": r.start_time.isoformat(),
            "expired": datetime.utcnow() > r.expired_at if r.expired_at else False
        })
    return {"count": total, "results": result}

@router.get("/{record_id}")
def get_record_detail(record_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(TrainingRecord).filter(TrainingRecord.id == record_id, TrainingRecord.user_id == current_user["id"]).first()
    if not record:
        raise HTTPException(404)
    epochs = db.query(TrainingEpoch).filter(TrainingEpoch.record_id == record_id).order_by(TrainingEpoch.epoch).all()
    return {
        "id": record.id,
        "model_type": record.model_type,
        "hidden_layer_sizes": record.hidden_layer_sizes,
        "max_iter": record.max_iter,
        "learning_rate": record.learning_rate,
        "data_path": record.data_path,
        "status": record.status,
        "final_error": record.final_error,
        "final_accuracy": record.final_accuracy,
        "final_mae": record.final_mae,
        "start_time": record.start_time.isoformat(),
        "end_time": record.end_time.isoformat() if record.end_time else None,
        "epochs": [{"epoch": e.epoch, "error": e.error, "accuracy": e.accuracy, "training_duration": e.training_duration} for e in epochs]
    }

@router.get("/{record_id}/export")
def export_record(record_id: int, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.query(TrainingRecord).filter(TrainingRecord.id == record_id, TrainingRecord.user_id == current_user["id"]).first()
    if not record:
        raise HTTPException(404)
    if record.expired_at and datetime.utcnow() > record.expired_at:
        raise HTTPException(403, "记录已超过一年，不可下载")
    epochs = db.query(TrainingEpoch).filter(TrainingEpoch.record_id == record_id).order_by(TrainingEpoch.epoch).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["epoch", "error", "accuracy", "training_duration"])
    for e in epochs:
        writer.writerow([e.epoch, e.error, e.accuracy, e.training_duration])
    response = Response(content=output.getvalue(), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=training_{record_id}.csv"
    return response