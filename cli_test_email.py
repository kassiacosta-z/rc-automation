#!/usr/bin/env python3
"""
CLI: Envia email de teste usando EmailService
"""
import argparse
from services.email_service import EmailService


def main():
    parser = argparse.ArgumentParser(description="Enviar email de teste")
    parser.add_argument("--to", dest="to", required=True, help="Email destino")
    args = parser.parse_args()

    es = EmailService()
    res = es.send_email([args.to], subject="Teste - Automação de Recibos", body="Teste de envio OK.")
    print(res)


if __name__ == "__main__":
    main()


