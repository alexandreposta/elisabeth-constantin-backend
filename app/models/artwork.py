from pydantic import BaseModel, Field
from typing import Optional, List

class Artwork(BaseModel):
    title: str
    description: Optional[str] = None
    main_image: str
    other_images: Optional[List[str]] = []
    price: float
    width: float  # en cm
    height: float  # en cm
    type: str = "peinture"  # Permet maintenant n'importe quelle chaîne
    is_available: bool = True

class ArtworkInDB(Artwork):
    id: str = Field(..., alias="_id")

class UpdateTypeRequest(BaseModel):
    oldType: str
    newType: str