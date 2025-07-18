#!/bin/bash

# Script de déploiement backend sur Vercel
echo "🚀 Déploiement Backend Elisabeth Constantin"

# Vérifier si Vercel CLI est installé
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI n'est pas installé. Installez-le avec: npm i -g vercel"
    exit 1
fi

# Déploiement
echo "🚀 Déploiement sur Vercel..."
vercel --prod

echo "✅ Déploiement terminé!"
echo "🔗 N'oubliez pas de configurer les variables d'environnement dans le dashboard Vercel:"
echo "   - MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/site_maman"
echo "   - MONGO_DB=site_maman"
echo "   - STRIPE_SECRET_KEY=sk_live_..."
echo "   - ADMIN_EMAIL=your-admin-email@example.com"
