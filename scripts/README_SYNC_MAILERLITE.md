# Synchronisation MailerLite

Ce dossier contient les outils pour synchroniser les statuts des abonnés entre MailerLite et notre base de données.

## 🔄 Méthodes de synchronisation

### 1. Webhook MailerLite (Recommandé - Temps réel)

Le webhook reçoit automatiquement les notifications de MailerLite quand un subscriber change de statut.

#### Configuration dans MailerLite

1. Allez dans **Settings** → **Integrations** → **Webhooks**
2. Créez un nouveau webhook avec l'URL : `https://votre-domaine.fr/api/webhooks/mailerlite/subscriber-updated`
3. Sélectionnez les événements :
   - ✅ `subscriber.double_opt_in` (confirmation d'email)
   - ✅ `subscriber.unsubscribed` (désinscription)
   - ✅ `subscriber.bounced` (email invalide)
   - ✅ `subscriber.complaint` (spam)
4. (Optionnel) Copiez le secret et ajoutez-le dans votre `.env` :
   ```
   MAILERLITE_WEBHOOK_SECRET=votre_secret_ici
   ```

#### Ce que fait le webhook

- **Double opt-in confirmé** → Passe le subscriber en `confirmed` dans la DB et génère un code promo
- **Unsubscribed** → Passe le subscriber en `unsubscribed`
- **Bounced** → Marque l'email comme invalide
- **Complaint** → Marque l'email comme spam

### 2. Script de synchronisation manuelle (Backup)

Si les webhooks ne sont pas configurés ou pour une vérification périodique.

#### Exécution manuelle

```bash
cd /home/alexandre/site_maman/elisabeth-constantin-backend
python scripts/sync_mailerlite_status.py
```

#### Automatisation avec cron (recommandé)

Ajoutez dans votre crontab (toutes les heures) :

```bash
crontab -e
```

Puis ajoutez :

```bash
0 * * * * cd /home/alexandre/site_maman/elisabeth-constantin-backend && /usr/bin/python3 scripts/sync_mailerlite_status.py >> /tmp/mailerlite_sync.log 2>&1
```

## 🔍 Vérifier la synchronisation

### Vérifier le statut d'un email spécifique

```bash
# Dans votre backend, utilisez MongoDB
mongosh
use elisabeth_constantin
db.subscribers.findOne({email: "alexandre200413@gmail.com"})
```

### Vérifier les logs du webhook

Les logs du webhook sont dans les logs de votre application FastAPI.

### Tester le webhook localement

```bash
curl -X POST http://localhost:8000/api/webhooks/mailerlite/subscriber-updated \
  -H "Content-Type: application/json" \
  -d '{
    "events": [{
      "type": "subscriber.double_opt_in",
      "data": {
        "subscriber": {
          "email": "test@example.com",
          "status": "active"
        }
      }
    }]
  }'
```

## 📊 Statuts

### MailerLite → Notre DB

| MailerLite | Notre DB | Description |
|------------|----------|-------------|
| `active` | `confirmed` | Email confirmé, peut recevoir des newsletters |
| `unconfirmed` | `pending` | En attente de confirmation |
| `unsubscribed` | `unsubscribed` | Désinscrit |
| `bounced` | `bounced` | Email invalide |
| `junk` | `complained` | Marqué comme spam |

## 🚀 Déploiement

### Variables d'environnement nécessaires

```bash
MAILERLITE_PRIVATE_KEY=votre_api_key
MAILERLITE_NEWSLETTER_GROUP=newsletter_site
MAILERLITE_WEBHOOK_SECRET=votre_secret_webhook  # Optionnel mais recommandé
```

### Sur Vercel

Le webhook est automatiquement déployé avec votre API. Utilisez l'URL :
```
https://elisabeth-constantin.fr/api/webhooks/mailerlite/subscriber-updated
```

## 🐛 Dépannage

### Le statut ne se met pas à jour

1. Vérifiez que le webhook est bien configuré dans MailerLite
2. Vérifiez les logs de votre application
3. Exécutez le script de synchronisation manuelle
4. Vérifiez que l'email existe bien dans votre DB

### Erreur 401 sur le webhook

Le secret du webhook ne correspond pas. Vérifiez `MAILERLITE_WEBHOOK_SECRET` dans votre `.env`.

### Le script de synchronisation ne trouve pas les subscribers

Vérifiez que :
- `MAILERLITE_PRIVATE_KEY` est correctement configuré
- `MAILERLITE_NEWSLETTER_GROUP` correspond au nom du groupe dans MailerLite
- Votre connexion MongoDB fonctionne
