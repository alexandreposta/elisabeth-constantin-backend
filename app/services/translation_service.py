import os
import requests
import logging
from typing import Optional
from app.models.translation import TranslationRequest, TranslationResponse, SupportedLanguage

logger = logging.getLogger(__name__)

class DeepLService:
    def __init__(self):
        self.api_key = os.getenv('DEEPL_API_KEY')
        self.api_url = os.getenv('DEEPL_API_URL', 'https://api-free.deepl.com/v2/translate')
        
        if not self.api_key:
            logger.warning("DEEPL_API_KEY not found in environment variables. Translation service will be disabled.")
    
    async def translate_text(self, request: TranslationRequest) -> Optional[TranslationResponse]:
        """
        Traduit un texte en utilisant l'API DeepL
        """
        if not self.api_key:
            logger.error("DeepL API key not configured")
            return None
        
        try:
            # Mapping des codes de langue pour DeepL
            deepl_lang_map = {
                SupportedLanguage.FRENCH: "FR",
                SupportedLanguage.ENGLISH: "EN"
            }
            
            headers = {
                'Authorization': f'DeepL-Auth-Key {self.api_key}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            data = {
                'text': request.text,
                'source_lang': deepl_lang_map[request.source_language],
                'target_lang': deepl_lang_map[request.target_language],
                'preserve_formatting': '1'
            }
            
            logger.info(f"Translating text from {request.source_language} to {request.target_language}")
            
            response = requests.post(self.api_url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            
            if 'translations' in result and len(result['translations']) > 0:
                translated_text = result['translations'][0]['text']
                
                return TranslationResponse(
                    original_text=request.text,
                    translated_text=translated_text,
                    source_language=request.source_language,
                    target_language=request.target_language,
                    is_automatic=True
                )
            else:
                logger.error("No translation found in DeepL response")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("DeepL API request timeout")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepL API request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during translation: {str(e)}")
            return None
    
    async def get_api_usage(self) -> Optional[dict]:
        """
        Récupère les informations d'utilisation de l'API DeepL
        """
        if not self.api_key:
            return None
        
        try:
            usage_url = self.api_url.replace('/v2/translate', '/v2/usage')
            headers = {
                'Authorization': f'DeepL-Auth-Key {self.api_key}'
            }
            
            response = requests.get(usage_url, headers=headers, timeout=5)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error fetching DeepL usage: {str(e)}")
            return None

# Instance globale du service
deepl_service = DeepLService()
