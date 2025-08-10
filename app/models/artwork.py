from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class ArtworkStatus(str, Enum):
    AVAILABLE = "Disponible"
    SOLD = "Vendu"
    UNAVAILABLE = "Indisponible"

class Artwork(BaseModel):
    title: str
    description: Optional[str] = None
    main_image: str
    other_images: Optional[List[str]] = []
    price: float
    width: float  # en cm
    height: float  # en cm
    type: str = "peinture"  # Permet maintenant n'importe quelle chaîne
    status: ArtworkStatus = ArtworkStatus.AVAILABLE

class ArtworkInDB(Artwork):
    id: str = Field(..., alias="_id")
    
    class Config:
        allow_population_by_field_name = True
        populate_by_name = True

class UpdateTypeRequest(BaseModel):
    oldType: str
    newType: str