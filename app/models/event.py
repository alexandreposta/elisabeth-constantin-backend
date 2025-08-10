from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
from .translation import Translation

class EventStatus(str, Enum):
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Event(BaseModel):
    title: str
    title_translations: Optional[Translation] = None
    description: str
    description_translations: Optional[Translation] = None
    start_date: datetime
    end_date: datetime
    location: str
    start_time: str  # Format "HH:MM"
    end_time: str    # Format "HH:MM"
    main_image: str
    status: EventStatus = EventStatus.UPCOMING
    is_active: bool = True

class EventInDB(Event):
    id: str = Field(..., alias="_id")
