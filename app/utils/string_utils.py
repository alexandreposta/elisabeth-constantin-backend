import re
import unicodedata


def normalize_string(value: str) -> str:
    """
    Normalise une chaîne pour comparaison dans les URLs et recherches:
    - convertit en str
    - passe en minuscules
    - retire les accents
    - garde uniquement les caractères alphanumériques (a-z0-9)
    - supprime les espaces, tirets et underscores
    Exemple: 'Plan 3D' -> 'plan3d'
    """
    if value is None:
        return ""
    s = str(value)
    # décomposer les accents
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    # garder uniquement lettres et chiffres
    s = re.sub(r'[^a-z0-9]+', '', s)
    return s
