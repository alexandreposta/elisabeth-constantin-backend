from app.database import get_database
from app.models.translation import Translation, TranslationInDB, SupportedLanguage
from app.models.artwork import Artwork
from app.models.event import Event
from app.services.translation_service import deepl_service
from bson import ObjectId
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

def get_or_create_translation(entity_type: str, entity_id: str, field_name: str, source_text: str) -> Translation:
    """
    Récupère une traduction existante ou en crée une nouvelle
    (Version synchrone simplifiée pour compatibilité avec PyMongo)
    """
    try:
        database = get_database()
        # Rechercher une traduction existante
        existing = database.translations.find_one({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "field_name": field_name
        })
        
        if existing:
            return Translation(
                fr=existing.get("fr", source_text),
                en=existing.get("en"),
                en_manual=existing.get("en_manual", False)
            )
        
        # Créer une nouvelle traduction (sans traduction automatique pour l'instant)
        translation = Translation(
            fr=source_text,
            en=None,
            en_manual=False
        )
        
        # Document pour la base de données
        translation_doc = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "field_name": field_name,
            "fr": source_text,
            "en": None,
            "en_manual": False
        }
        
        # Sauvegarder la traduction en base
        database.translations.insert_one(translation_doc)
        
        return translation
        
    except Exception as e:
        logger.error(f"Error in get_or_create_translation: {str(e)}")
        return Translation(fr=source_text, en=None, en_manual=False)

def update_manual_translation(
    entity_type: str, 
    entity_id: str, 
    field_name: str, 
    language: SupportedLanguage, 
    translated_text: str
) -> bool:
    """
    Met à jour une traduction manuelle
    """
    try:
        database = get_database()
        update_data = {
            f"{language}": translated_text,
            f"{language}_manual": True
        }
        
        result = database.translations.update_one(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "field_name": field_name
            },
            {
                "$set": update_data
            },
            upsert=True
        )
        
        return result.acknowledged
        
    except Exception as e:
        logger.error(f"Error updating manual translation: {str(e)}")
        return False

def get_translations_by_entity(entity_type: str, entity_id: str) -> List[TranslationInDB]:
    """
    Récupère toutes les traductions pour une entité donnée
    """
    try:
        database = get_database()
        cursor = database.translations.find({
            "entity_type": entity_type,
            "entity_id": entity_id
        })
        
        translations = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            translations.append(TranslationInDB(**doc))
        
        return translations
        
    except Exception as e:
        logger.error(f"Error getting translations by entity: {str(e)}")
        return []

def delete_translations_by_entity(entity_type: str, entity_id: str) -> bool:
    """
    Supprime toutes les traductions d'une entité
    """
    try:
        database = get_database()
        result = database.translations.delete_many({
            "entity_type": entity_type,
            "entity_id": entity_id
        })
        
        return result.acknowledged
        
    except Exception as e:
        logger.error(f"Error deleting translations: {str(e)}")
        return False

def get_translated_content(entity_type: str, entity_id: str, language: SupportedLanguage) -> Optional[dict]:
    """
    Récupère le contenu traduit pour une entité dans la langue spécifiée
    Retourne l'entité complète avec les champs traduits remplacés
    """
    try:
        database = get_database()
        
        # Récupérer l'entité source
        if entity_type == "artwork":
            entity = database.artworks.find_one({"_id": ObjectId(entity_id)})
        elif entity_type == "event":
            entity = database.events.find_one({"_id": ObjectId(entity_id)})
        else:
            return None
        
        if not entity:
            return None
        
        # Si la langue demandée est le français, retourner l'entité originale
        if language == SupportedLanguage.FRENCH:
            return entity
        
        # Pour l'anglais, récupérer les traductions
        if language == SupportedLanguage.ENGLISH:
            # Récupérer toutes les traductions pour cette entité
            translations = database.translations.find({
                "entity_type": entity_type,
                "entity_id": entity_id
            })
            
            # Créer une copie de l'entité pour la modifier
            translated_entity = dict(entity)
            
            # Appliquer les traductions disponibles
            for translation_doc in translations:
                field_name = translation_doc.get("field_name")
                en_translation = translation_doc.get("en")
                
                if field_name and en_translation:
                    translated_entity[field_name] = en_translation
            
            return translated_entity
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting translated content: {str(e)}")
        return None

def refresh_automatic_translations(entity_type: str, entity_id: str) -> bool:
    """
    Actualise les traductions automatiques (pas les manuelles)
    """
    try:
        database = get_database()
        # Récupérer l'entité source
        if entity_type == "artwork":
            entity = database.artworks.find_one({"_id": ObjectId(entity_id)})
        elif entity_type == "event":
            entity = database.events.find_one({"_id": ObjectId(entity_id)})
        else:
            return False
        
        if not entity:
            return False
        
        # Actualiser les traductions pour title et description
        fields_to_translate = ["title", "description"]
        
        for field in fields_to_translate:
            if field in entity and entity[field]:
                # Récupérer la traduction existante
                existing = database.translations.find_one({
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "field_name": field
                })
                
                # Ne pas actualiser les traductions manuelles
                if existing and existing.get("en_manual", False):
                    continue
                
                # Créer une nouvelle traduction automatique
                get_or_create_translation(entity_type, entity_id, field, entity[field])
        
        return True
        
    except Exception as e:
        logger.error(f"Error refreshing automatic translations: {str(e)}")
        return False
