from pydantic import BaseModel, Field
from typing import Optional, Dict
from enum import Enum

class SupportedLanguage(str, Enum):
    FRENCH = "fr"
    ENGLISH = "en"

class Translation(BaseModel):
    fr: str  # Texte français (langue principale)
    en: Optional[str] = None  # Traduction anglaise
    en_manual: Optional[bool] = False  # True si traduit manuellement par l'admin

class TranslationInDB(Translation):
    id: str = Field(..., alias="_id")
    entity_type: str  # "artwork" ou "event"
    entity_id: str  # ID de l'artwork ou event concerné
    field_name: str  # "title" ou "description"

class TranslationRequest(BaseModel):
    text: str
    source_language: SupportedLanguage = SupportedLanguage.FRENCH
    target_language: SupportedLanguage = SupportedLanguage.ENGLISH

class TranslationResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    target_language: str
    is_automatic: bool = True

class ManualTranslationUpdate(BaseModel):
    entity_type: str
    entity_id: str
    field_name: str
    language: SupportedLanguage
    translated_text: str
