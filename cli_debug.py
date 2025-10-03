#!/usr/bin/env python3
"""
CLI: Debug detalhado do Gmail (query, paginação, primeiros headers)
"""
import argparse
import os
import sys
from config import config
from services.gmail_service import GmailService


def main():
    parser = argparse.ArgumentParser(description="Debug da busca de recibos no Gmail")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--max", dest="max_results", type=int, default=20)
    parser.add_argument("--oauth2", action="store_true")
    args = parser.parse_args()

    print("=== Debug Gmail ===")
    print(f"Monitora: {config.GMAIL_MONITORED_EMAIL}")

    try:
        if args.oauth2 or (os.path.exists("oauth2_credentials.json")):
            gs = GmailService("oauth2_credentials.json", use_oauth2=True)
            print("Auth: OAuth2")
        else:
            gs = GmailService(config.GOOGLE_CREDENTIALS_JSON, delegated_user=config.GMAIL_DELEGATED_USER)
            print("Auth: Service Account")
    except Exception as e:
        print("Erro init GmailService:", e)
        sys.exit(1)

    try:
        q = gs._build_receipt_search_query(args.days)
        print("Query:", q)
        resp = gs.list_receipt_messages(
            config.GMAIL_MONITORED_EMAIL,
            max_results=args.max_results,
            days_back=args.days,
        )
        msgs = resp.get("messages", [])
        print(f"Mensagens encontradas: {len(msgs)}")
        if msgs:
            for i, m in enumerate(msgs[:5]):
                full = gs.get_message(config.GMAIL_MONITORED_EMAIL, m["id"])
                basic = gs._extract_basic_email_data(full)
                print(
                    f"{i+1}. id={m['id']} | from={basic.get('from')} | subject={basic.get('subject')} | date={basic.get('date')}"
                )
        else:
            print("Nenhuma mensagem retornada.")
    except Exception as e:
        print("Erro na listagem:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()


