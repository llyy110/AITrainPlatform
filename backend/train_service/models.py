from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class TrainingRecord(Base):
    __tablename__ = "training_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    task_id = Column(String(64), unique=True, index=True)
    model_type = Column(String(50))
    hidden_layer_sizes = Column(Integer)
    max_iter = Column(Integer)
    learning_rate = Column(Float)
    data_path = Column(Text)
    status = Column(String(20), default="pending")
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    final_error = Column(Float, nullable=True)
    final_accuracy = Column(Float, nullable=True)
    final_mae = Column(Float, nullable=True)
    model_save_path = Column(Text, nullable=True)
    training_log_path = Column(Text, nullable=True)
    expired_at = Column(DateTime, nullable=True)  # 创建时间 + 1年

class TrainingEpoch(Base):
    __tablename__ = "training_epochs"
    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("training_records.id"))
    epoch = Column(Integer)
    error = Column(Float)
    accuracy = Column(Float, nullable=True)
    training_duration = Column(Float)
    data_loading_duration = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)