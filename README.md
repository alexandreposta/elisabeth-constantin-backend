# Elisabeth Constantin - Backend API

API REST Python/FastAPI pour le site web d'Elisabeth Constantin, artiste peintre.

## 🚀 Déploiement sur Vercel

### Variables d'environnement requises

Configurez ces variables dans votre dashboard Vercel :

```bash
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/site_maman?retryWrites=true&w=majority
MONGO_DB=site_maman
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key_here
ADMIN_EMAIL=your-admin-email@example.com
```

### Configuration automatique Vercel

Ce projet est configuré pour un déploiement automatique sur Vercel avec :
- Build command: `pip install -r requirements.txt`
- Python version: 3.11
- Entry point: `app/main.py`

## 🛠️ Développement local

1. Clonez le repository
2. Créez un environnement virtuel : `python -m venv venv`
3. Activez l'environnement : `source venv/bin/activate` (Linux/Mac) ou `venv\Scripts\activate` (Windows)
4. Installez les dépendances : `pip install -r requirements.txt`
5. Copiez `.env.example` vers `.env` et configurez les variables
6. Initialisez l'admin : `python init_admin.py`
7. Lancez le serveur : `uvicorn app.main:app --reload`

## 📦 Dépendances principales

- FastAPI - Framework web moderne
- MongoDB/Motor - Base de données
- Stripe - Paiements
- Cloudinary - Gestion d'images
- JWT - Authentification
- Pydantic - Validation des données

## 🔧 Endpoints API

### Artworks
- `GET /api/artworks` - Liste des œuvres
- `POST /api/artworks` - Créer une œuvre (admin)
- `PUT /api/artworks/{id}` - Modifier une œuvre (admin)
- `DELETE /api/artworks/{id}` - Supprimer une œuvre (admin)

### Orders
- `POST /api/orders/create-payment-intent` - Créer une intention de paiement
- `GET /api/orders` - Liste des commandes (admin)
- `PUT /api/orders/{id}/status` - Modifier le statut (admin)

### Events
- `GET /api/events` - Liste des événements
- `POST /api/events` - Créer un événement (admin)
- `PUT /api/events/{id}` - Modifier un événement (admin)
- `DELETE /api/events/{id}` - Supprimer un événement (admin)

### Admin
- `POST /api/admin/login` - Connexion admin
- `GET /api/admin/me` - Profil admin

### Analytics
- `POST /api/analytics/track` - Enregistrer une visite
- `GET /api/analytics/stats` - Statistiques (admin)

## 🔒 Sécurité

- Variables d'environnement pour les secrets
- JWT pour l'authentification admin
- Validation Pydantic sur tous les endpoints
- CORS configuré pour le frontend
- Clés Stripe en mode production
- Chiffrement des mots de passe avec bcrypt

## 📊 Base de données

Structure MongoDB :
- `artworks` - Œuvres d'art
- `orders` - Commandes
- `events` - Événements
- `admins` - Comptes administrateur
- `analytics` - Données de visite

## 🔍 Monitoring

- Logs structurés avec FastAPI
- Gestion d'erreurs centralisée
- Validation des données d'entrée
- Rate limiting (à implémenter)

## 🚀 Production

Optimisations pour la production :
- Mode production FastAPI
- Gestion des CORS
- Variables d'environnement sécurisées
- Monitoring des erreurs
