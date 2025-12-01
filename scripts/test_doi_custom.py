"""
Test double opt-in avec email personnalisé.

Usage:
    python scripts/test_doi_custom.py votre.email@example.com
"""

import sys
sys.path.insert(0, '/app')

from app.services.email.mailerlite_client import (
    ensure_group,
    upsert_subscriber,
    get_subscriber,
    list_group_subscribers
)

def test_with_email(email: str):
    print("=" * 70)
    print(f"TEST DOUBLE OPT-IN AVEC: {email}")
    print("=" * 70)
    
    # Vérifier le groupe
    group_id = ensure_group('newsletter_site')
    print(f"\n📁 Groupe: newsletter_site (ID: {group_id})")
    
    # Créer le subscriber
    print(f"\n🔄 Création du subscriber avec status='unconfirmed'...")
    result = upsert_subscriber(
        email=email,
        status="unconfirmed",
        groups=[group_id]
    )
    
    if not result:
        print("❌ Échec de la création du subscriber")
        return
    
    print(f"\n✅ Subscriber créé avec succès:")
    print(f"   ID: {result.get('id')}")
    print(f"   Email: {result.get('email')}")
    print(f"   Status: {result.get('status')}")
    print(f"   Created at: {result.get('created_at')}")
    
    print("\n" + "=" * 70)
    print("VÉRIFICATION:")
    print("=" * 70)
    print("\n1. Vérifiez votre boîte mail (et dossier spam)")
    print("2. Vous devriez recevoir un email de confirmation MailerLite")
    print("3. Si vous ne recevez RIEN:")
    print("   → Le double opt-in API n'est PAS vraiment activé")
    print("   → Ou l'email de confirmation n'est pas configuré")
    print("   → Ou il y a un problème avec l'expéditeur vérifié")
    
    print("\n📊 État actuel du groupe:")
    subscribers = list_group_subscribers(group_id, status='unconfirmed')
    print(f"   Total unconfirmed: {len(subscribers)}")
    
    active_subscribers = list_group_subscribers(group_id, status='active')
    print(f"   Total active: {len(active_subscribers)}")
    
    print("\n" + "=" * 70)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_doi_custom.py votre.email@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    test_with_email(email)
