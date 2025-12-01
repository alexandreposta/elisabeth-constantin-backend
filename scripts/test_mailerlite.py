#!/usr/bin/env python3
"""
Script de debug pour tester l'intégration MailerLite depuis l'environnement du backend.

Usage:
  python scripts/test_mailerlite.py [optional_email]

Ce script :
  - affiche si la clé API est présente
  - liste les groupes existants
  - tente d'assurer (create/get) le groupe `MAILERLITE_NEWSLETTER_GROUP`
  - optionnellement récupère l'abonné pour l'email fourni
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app.services.email import mailerlite_client


def main():
    api_key = os.getenv("MAILERLITE_PRIVATE_KEY")
    group_name = os.getenv("MAILERLITE_NEWSLETTER_GROUP", "newsletter_site")

    print("MAILERLITE_PRIVATE_KEY present:", bool(api_key))
    print("Using group:", group_name)

    try:
        groups = mailerlite_client.list_groups(limit=50)
        print(f"Found {len(groups)} groups")
        for g in groups[:20]:
            print(" -", g.get("name"), g.get("id"))

        gid = mailerlite_client.ensure_group(group_name)
        print("ensure_group returned id:", gid)

        if len(sys.argv) > 1:
            email = sys.argv[1]
            sub = mailerlite_client.get_subscriber(email)
            print(f"Subscriber for {email}:", sub)

    except Exception as e:
        print("Error calling MailerLite client:", e)


if __name__ == '__main__':
    main()
