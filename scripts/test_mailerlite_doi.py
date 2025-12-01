"""
Script de diagnostic pour tester le double opt-in MailerLite.
Crée un subscriber de test et vérifie s'il reçoit l'email de confirmation.

Usage:
    python scripts/test_mailerlite_doi.py
"""

import sys
sys.path.insert(0, '/app')

import time
from app.services.email.mailerlite_client import (
    ensure_group,
    upsert_subscriber,
    get_subscriber,
    _request
)

def test_double_optin():
    print("=" * 70)
    print("TEST DOUBLE OPT-IN MAILERLITE")
    print("=" * 70)
    
    # Email de test
    test_email = f"test-doi-{int(time.time())}@example.com"
    print(f"\n📧 Email de test: {test_email}")
    
    # Vérifier le groupe
    group_id = ensure_group('newsletter_site')
    print(f"📁 Groupe: newsletter_site (ID: {group_id})")
    
    # Créer le subscriber avec status=unconfirmed
    print(f"\n🔄 Création du subscriber avec status='unconfirmed'...")
    result = upsert_subscriber(
        email=test_email,
        status="unconfirmed",
        groups=[group_id]
    )
    
    if not result:
        print("❌ Échec de la création du subscriber")
        return
    
    print(f"✅ Subscriber créé:")
    print(f"   ID: {result.get('id')}")
    print(f"   Email: {result.get('email')}")
    print(f"   Status: {result.get('status')}")
    print(f"   Created at: {result.get('created_at')}")
    print(f"   Groups: {[g.get('name') for g in result.get('groups', [])]}")
    
    print("\n" + "=" * 70)
    print("DIAGNOSTIC:")
    print("=" * 70)
    
    if result.get('status') == 'unconfirmed':
        print("\n✅ Le subscriber est bien créé avec status='unconfirmed'")
        print("\n⚠️  SI VOUS NE RECEVEZ PAS D'EMAIL DE CONFIRMATION:")
        print("\n1. Vérifiez que le double opt-in API est activé dans MailerLite:")
        print("   → https://dashboard.mailerlite.com")
        print("   → Account Settings (avatar en haut à droite)")
        print("   → Subscribe Settings (menu gauche)")
        print("   → Toggle 'Double opt-in for API and integrations' doit être ON ✅")
        print("\n2. Vérifiez l'email de confirmation personnalisé:")
        print("   → Dans Subscribe Settings")
        print("   → Onglet 'Confirmation email'")
        print("   → Cliquez 'Edit' pour voir/modifier le template")
        print("\n3. Vérifiez que l'expéditeur est vérifié:")
        print(f"   → {result.get('source', 'N/A')}")
        print("\n4. Testez avec un vrai email (pas @example.com):")
        print("   → Les emails @example.com peuvent être bloqués")
        
    else:
        print(f"\n❌ Le subscriber n'est PAS 'unconfirmed' mais '{result.get('status')}'")
        print("   Cela peut indiquer que MailerLite l'a automatiquement activé")
    
    print("\n" + "=" * 70)
    print("Pour tester avec VOTRE EMAIL, relancez ce script")
    print("et changez test_email par votre vraie adresse.")
    print("=" * 70)

if __name__ == '__main__':
    test_double_optin()
