"""
Script pour synchroniser les subscribers entre MongoDB et MailerLite.
Utile pour corriger les désynchronisations.

Usage:
    python scripts/sync_subscribers.py [--dry-run] [--clean]
    
Options:
    --dry-run    Afficher les actions sans les exécuter
    --clean      Supprimer les subscribers de test (@example.com)
"""

import sys
sys.path.insert(0, '/app')

import argparse
from app.repositories.subscriber_repo import subscriber_repo
from app.services.email.mailerlite_client import (
    ensure_newsletter_subscriber,
    get_subscriber,
    list_group_subscribers,
    ensure_group,
    mark_subscriber_confirmed,
)

def sync_subscribers(dry_run=False, clean_test=False):
    """Synchronise MongoDB vers MailerLite"""
    
    print("=" * 60)
    print("SYNCHRONISATION SUBSCRIBERS MongoDB → MailerLite")
    print("=" * 60)
    
    # Récupérer tous les subscribers MongoDB
    mongo_subscribers = list(subscriber_repo.collection.find())
    print(f"\n📊 Total subscribers MongoDB: {len(mongo_subscribers)}")
    
    # Récupérer le groupe MailerLite
    group_id = ensure_group('newsletter_site')
    mailerlite_subscribers = list_group_subscribers(group_id, limit=200)
    mailerlite_emails = {s.get('email'): s for s in mailerlite_subscribers}
    print(f"📊 Total subscribers MailerLite: {len(mailerlite_subscribers)}\n")
    
    # Statistiques
    to_add = []
    to_update = []
    to_clean = []
    already_synced = []
    
    for sub in mongo_subscribers:
        email = sub.get('email')
        mongo_status = sub.get('status')
        
        # Nettoyer les emails de test si demandé
        if clean_test and '@example.com' in email:
            to_clean.append(email)
            continue
        
        # Vérifier si existe dans MailerLite
        ml_sub = mailerlite_emails.get(email)
        
        if not ml_sub:
            to_add.append((email, mongo_status))
        else:
            ml_status = ml_sub.get('status')
            # Synchroniser le statut
            if mongo_status == 'confirmed' and ml_status != 'active':
                to_update.append((email, mongo_status, ml_status))
            else:
                already_synced.append(email)
    
    # Afficher le résumé
    print("📋 RÉSUMÉ DES ACTIONS:")
    print(f"  ✅ Déjà synchronisés: {len(already_synced)}")
    print(f"  ➕ À ajouter à MailerLite: {len(to_add)}")
    print(f"  🔄 À mettre à jour: {len(to_update)}")
    if clean_test:
        print(f"  🗑️  À nettoyer (test emails): {len(to_clean)}")
    print()
    
    # Afficher les détails
    if to_add:
        print("\n➕ SUBSCRIBERS À AJOUTER:")
        for email, status in to_add:
            print(f"  • {email} (status: {status})")
    
    if to_update:
        print("\n🔄 SUBSCRIBERS À METTRE À JOUR:")
        for email, mongo_status, ml_status in to_update:
            print(f"  • {email}: MongoDB={mongo_status} → MailerLite={ml_status}")
    
    if to_clean:
        print("\n🗑️  SUBSCRIBERS À NETTOYER:")
        for email in to_clean:
            print(f"  • {email}")
    
    # Exécuter les actions
    if dry_run:
        print("\n⚠️  MODE DRY-RUN - Aucune action exécutée")
        return
    
    print("\n" + "=" * 60)
    print("EXÉCUTION DES ACTIONS")
    print("=" * 60)
    
    # Ajouter les subscribers manquants
    for email, mongo_status in to_add:
        try:
            print(f"\n➕ Ajout de {email}...")
            if mongo_status == 'confirmed':
                # Ajouter directement comme active
                result = ensure_newsletter_subscriber(email)
                if result:
                    mark_subscriber_confirmed(email)
                    print(f"  ✅ Ajouté et confirmé")
            else:
                # Ajouter avec double opt-in
                result = ensure_newsletter_subscriber(email)
                if result:
                    print(f"  ✅ Ajouté (pending confirmation)")
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
    
    # Mettre à jour les statuts
    for email, mongo_status, ml_status in to_update:
        try:
            print(f"\n🔄 Mise à jour de {email}...")
            if mongo_status == 'confirmed':
                mark_subscriber_confirmed(email)
                print(f"  ✅ Statut mis à jour: {ml_status} → active")
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
    
    # Nettoyer les emails de test
    if clean_test:
        for email in to_clean:
            try:
                print(f"\n🗑️  Suppression de {email}...")
                subscriber_repo.collection.delete_one({'email': email})
                print(f"  ✅ Supprimé de MongoDB")
            except Exception as e:
                print(f"  ❌ Erreur: {e}")
    
    print("\n" + "=" * 60)
    print("✅ SYNCHRONISATION TERMINÉE")
    print("=" * 60)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Synchroniser les subscribers MongoDB → MailerLite')
    parser.add_argument('--dry-run', action='store_true', help='Afficher les actions sans les exécuter')
    parser.add_argument('--clean', action='store_true', help='Nettoyer les emails de test (@example.com)')
    
    args = parser.parse_args()
    
    sync_subscribers(dry_run=args.dry_run, clean_test=args.clean)
