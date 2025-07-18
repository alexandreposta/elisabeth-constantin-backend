"""
Utilitaires sécurisé pour la gestion CORS entre frontend et backend Vercel
"""

def get_cors_headers(origin_header=None):
    """
    Retourne les headers CORS sécurisés
    """
    allowed_origins = [
        'https://elisabeth-constantin-frontend.vercel.app',
        'https://site-maman-frontend.vercel.app', 
    ]
    
    # Vérifier si l'origine est autorisée
    if origin_header and origin_header in allowed_origins:
        return {
            'Access-Control-Allow-Origin': origin_header,
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Credentials': 'true'
        }
    else:
        # Fallback vers le domaine principal
        return {
            'Access-Control-Allow-Origin': 'https://elisabeth-constantin-frontend.vercel.app',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS', 
            'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            'Access-Control-Allow-Credentials': 'true'
        }

def apply_cors_headers(handler_instance, origin_header=None):
    """
    Applique les headers CORS à une réponse HTTP
    """
    headers = get_cors_headers(origin_header)
    for key, value in headers.items():
        handler_instance.send_header(key, value)
