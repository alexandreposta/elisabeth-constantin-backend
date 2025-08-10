from pydantic import BaseModel, Field
from typing import Optional

class ArtworkType(BaseModel):
    name: str
    display_name: Optional[str] = None
    is_active: bool = True

class ArtworkTypeInDB(ArtworkType):
    id: str = Field(..., alias="_id")

class CreateArtworkTypeRequest(BaseModel):
    name: str
    display_name: Optional[str] = None

class UpdateArtworkTypeRequest(BaseModel):
    display_name: Optional[str] = None
    is_active: Optional[bool] = None
