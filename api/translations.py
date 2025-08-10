from fastapi import APIRouter, HTTPException, status
from app.models.translation import (
    TranslationRequest, 
    TranslationResponse, 
    ManualTranslationUpdate,
    SupportedLanguage
)
from app.services.translation_service import deepl_service
from app.crud.translations import (
    update_manual_translation,
    get_translations_by_entity,
    refresh_automatic_translations
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/translate", response_model=TranslationResponse)
async def translate_text(request: TranslationRequest):
    """
    Traduit un texte en utilisant DeepL
    """
    try:
        logger.info(f"Translation request: {request.text[:50]}...")
        
        result = await deepl_service.translate_text(request)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Translation service unavailable"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in translate_text: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Translation failed"
        )

@router.post("/manual-update")
async def update_manual_translation_route(update: ManualTranslationUpdate):
    """
    Met à jour une traduction manuelle
    """
    try:
        logger.info(f"Manual translation update for {update.entity_type} {update.entity_id}")
        
        success = await update_manual_translation(
            update.entity_type,
            update.entity_id,
            update.field_name,
            update.language,
            update.translated_text
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update translation"
            )
        
        return {"message": "Translation updated successfully"}
        
    except Exception as e:
        logger.error(f"Error in update_manual_translation_route: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update translation"
        )

@router.get("/entity/{entity_type}/{entity_id}")
async def get_entity_translations(entity_type: str, entity_id: str):
    """
    Récupère toutes les traductions d'une entité
    """
    try:
        if entity_type not in ["artwork", "event"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid entity type"
            )
        
        translations = await get_translations_by_entity(entity_type, entity_id)
        return {"translations": translations}
        
    except Exception as e:
        logger.error(f"Error getting entity translations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get translations"
        )

@router.post("/refresh/{entity_type}/{entity_id}")
async def refresh_entity_translations(entity_type: str, entity_id: str):
    """
    Actualise les traductions automatiques d'une entité
    """
    try:
        if entity_type not in ["artwork", "event"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid entity type"
            )
        
        success = await refresh_automatic_translations(entity_type, entity_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to refresh translations"
            )
        
        return {"message": "Translations refreshed successfully"}
        
    except Exception as e:
        logger.error(f"Error refreshing translations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh translations"
        )

@router.get("/usage")
async def get_deepl_usage():
    """
    Récupère les informations d'utilisation de DeepL
    """
    try:
        usage = await deepl_service.get_api_usage()
        
        if usage is None:
            return {"message": "DeepL API not configured or unavailable"}
        
        return usage
        
    except Exception as e:
        logger.error(f"Error getting DeepL usage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage information"
        )
