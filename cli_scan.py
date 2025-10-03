#!/usr/bin/env python3
"""
CLI: Varredura de emails de recibos de IA e envio opcional de relatório
"""
import argparse
import json
import os
import sys
from datetime import datetime

from services.gmail_service import GmailService
from services.email_service import EmailService
from config import config


def main():
    parser = argparse.ArgumentParser(description="Varre emails de recibos de IA")
    parser.add_argument("--days", type=int, default=7, help="Dias para trás na busca (default: 7)")
    parser.add_argument("--max", dest="max_results", type=int, default=500, help="Máximo de emails a processar (default: 500)")
    parser.add_argument("--send", action="store_true", help="Enviar relatório por email ao final")
    parser.add_argument("--to", dest="target_email", default=os.getenv("REPORTS_EMAIL", "contasapagar@zello.tec.br"), help="Email destino do relatório")
    parser.add_argument("--oauth2", action="store_true", help="Força uso de OAuth2 (oauth2_credentials.json)")
    args = parser.parse_args()

    print("=== Varredura de Recibos - CLI ===")
    print(f"Email monitorado: {config.GMAIL_MONITORED_EMAIL}")
    print(f"Periodo: últimos {args.days} dias | Limite: {args.max_results}")

    # Inicializa GmailService
    try:
        if args.oauth2 or (os.path.exists("oauth2_credentials.json")):
            gs = GmailService("oauth2_credentials.json", use_oauth2=True)
            print("Auth: OAuth2")
        else:
            gs = GmailService(config.GOOGLE_CREDENTIALS_JSON, delegated_user=config.GMAIL_DELEGATED_USER)
            print("Auth: Service Account")
    except Exception as e:
        print(f"Erro ao inicializar GmailService: {e}")
        sys.exit(1)

    # Construir query e buscar mensagens
    try:
        query = gs._build_receipt_search_query(args.days)
        print(f"Query: {query}")
        page_token = None
        total = 0
        receipts = []
        while True:
            limit_this_page = min(100, max(0, args.max_results - total))
            if limit_this_page == 0:
                break
            resp = gs.list_receipt_messages(
                config.GMAIL_MONITORED_EMAIL,
                page_token=page_token,
                max_results=limit_this_page,
                days_back=args.days,
            )
            msgs = resp.get("messages", [])
            print(f"Página: +{len(msgs)} mensagens (acumulado: {total + len(msgs)})")
            for m in msgs:
                full = gs.get_message(config.GMAIL_MONITORED_EMAIL, m["id"])
                basic = gs._extract_basic_email_data(full)
                data = gs.receipt_extractor.extract_receipt_data(basic)
                receipts.append({"id": m["id"], "email": basic, "receipt": data})
                total += 1
                if total >= args.max_results:
                    break
            page_token = resp.get("nextPageToken")
            if not page_token or total >= args.max_results:
                break
        ok = [r for r in receipts if r["receipt"].get("success")]
        print(f"Total mensagens: {total} | Recibos válidos: {len(ok)}")
    except Exception as e:
        print(f"Erro na varredura: {e}")
        sys.exit(1)

    # Enviar relatório opcional
    if args.send and ok:
        try:
            es = EmailService()
            linhas = []
            for r in ok[:50]:
                rec = r["receipt"]
                linhas.append(
                    f"<tr><td>{rec.get('provedor')}</td><td>{rec.get('valor')}</td><td>{rec.get('data')}</td><td>{rec.get('numero_recibo')}</td><td>{r['email'].get('subject')}</td></tr>"
                )
            html = (
                "<html><body>"
                "<h2>Relatório de Recibos</h2>"
                f"<p>Gerado em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
                "<table border='1' cellpadding='6' cellspacing='0'>"
                "<tr><th>Provedor</th><th>Valor</th><th>Data</th><th>Número</th><th>Assunto</th></tr>"
                + "".join(linhas)
                + "</table></body></html>"
            )
            res = es.send_email([args.target_email], subject=f"Relatório de Recibos - {len(ok)} encontrados", body=html, is_html=True)
            print("Envio:", res)
        except Exception as e:
            print(f"Erro ao enviar relatório: {e}")
            sys.exit(1)

    # Saída JSON resumida
    print("\nResumo JSON:")
    print(
        json.dumps(
            {
                "messages_processed": total,
                "receipts_ok": len(ok),
                "sample": ok[:3],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()


