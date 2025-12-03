import json
import logging
import os
from typing import Dict, Iterable, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_TRANSLATION_MODEL", "gpt-4o-mini")

_client: Optional[OpenAI] = None

if OPENAI_API_KEY:
    try:
        _client = OpenAI(api_key=OPENAI_API_KEY)
        logger.info("OpenAI translation client initialised.")
    except Exception as exc:
        logger.error("Failed to initialise OpenAI client: %s", exc)
        _client = None
else:
    logger.warning("OPENAI_API_KEY is not set. Dynamic translations are disabled.")


def _translate_payload(payload: Dict[str, str], target_language: str) -> Dict[str, str]:
    """
    Translate a dictionary of strings using the OpenAI API while keeping the JSON structure intact.
    """
    if not payload or not _client:
        return {}

    prompt = (
        "Translate the following JSON object from French to {lang}. "
        "Keep the JSON structure and keys unchanged. "
        "Return valid JSON only without additional commentary.\n\n{data}"
    ).format(lang="English" if target_language == "en" else target_language, data=json.dumps(payload, ensure_ascii=False))

    try:
        completion = _client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional translator. Reply with valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = completion.choices[0].message.content.strip()
        # Certaines réponses peuvent être entourées de ```json ... ```
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        translated = json.loads(content)
        if isinstance(translated, dict):
            return translated
    except json.JSONDecodeError as exc:
        logger.error("Failed to decode translation JSON: %s", exc)
    except Exception as exc:
        logger.error("OpenAI translation error: %s", exc)
    return {}


def apply_dynamic_translations(
    document: dict,
    fields: Iterable[str],
    target_language: str,
    collection=None,
) -> dict:
    """
    Ensure the requested language exists for the given fields and update the database if needed.
    Returns a copy of the document with the translated values applied.
    """
    if not document or target_language == "fr":
        return dict(document) if document else document

    translations = document.get("translations", {})
    lang_translations = translations.get(target_language, {}) or {}
    fields_to_translate: Dict[str, str] = {}

    for field in fields:
        existing_value = lang_translations.get(field)
        source_value = document.get(field)
        if existing_value is None and source_value:
            fields_to_translate[field] = source_value

    if fields_to_translate:
        new_values = _translate_payload(fields_to_translate, target_language)
        if new_values:
            lang_translations.update(new_values)
            translations[target_language] = lang_translations
            if collection is not None and document.get("_id"):
                try:
                    collection.update_one(
                        {"_id": document["_id"]},
                        {"$set": {"translations": translations}},
                    )
        except Exception as exc:
            logger.error("Failed to persist translations: %s", exc)

    updated_document = dict(document)
    for field in fields:
        translated_value = lang_translations.get(field)
        if translated_value:
            updated_document[field] = translated_value
    return updated_document
