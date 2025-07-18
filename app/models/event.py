from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class EventStatus(str, Enum):
    UPCOMING = "upcoming"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Event(BaseModel):
    title: str
    description: str
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
