from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from enum import Enum
from uuid import uuid4

class JobMode(str, Enum):
    audio = "audio"
    video = "video"

class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    error = "error"
    canceled = "canceled"

class Job(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = Field(default_factory=lambda: uuid4().hex)
    urls: List[str]
    mode: JobMode = JobMode.video
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: JobStatus = JobStatus.queued
    progress: float = 0.0
    current: Optional[str] = None
    message: Optional[str] = None
    output_paths: List[str] = Field(default_factory=list)
    total_count: int = 0
    current_index: int = 0
