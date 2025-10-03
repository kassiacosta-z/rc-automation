#!/usr/bin/env python3
"""
Receipt Scraper: Login Gmail + Web Scraping
Baseado nos scripts financeiros que funcionam
"""
import argparse
import os
import re
import sys
import time
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class ReceiptScraper:
    def __init__(self):
        self.driver = None
        self.email = "iazello@zello.tec.br"
        self.password = "@Zello2025"
        
        # Fornecedores de IA
        self.ai_senders = [
            "noreply@openai.com", "billing@openai.com", "receipts@anthropic.com",
            "billing@cursor.com", "invoice+statements+acct_1R15XBHkfKp4fCS9@stripe.com",
            "help@paddle.com", "noreply@anthropic.com", "billing@anthropic.com"
        ]
        
        # Palavras-chave de recibos
        self.receipt_keywords = [
            "receipt", "invoice", "billing", "payment", "transaction",
            "recibo", "fatura", "cobrança", "pagamento", "transação"
        ]

    def criar_driver(self, headless=False, profile_dir=None):
        """Cria driver Chrome otimizado baseado nos scripts financeiros"""
        print("Criando driver Chrome...")
        
        chrome_options = Options()
        
        if headless:
            chrome_options.add_argument("--headless=new")
        else:
            chrome_options.add_argument("--start-maximized")
        
        # Configurações EXATAS dos scripts financeiros que funcionam
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript-harmony-shipping")
        chrome_options.page_load_strategy = 'eager'
        
        # Perfil persistente
        if profile_dir:
            os.makedirs(profile_dir, exist_ok=True)
            chrome_options.add_argument(f"--user-data-dir={os.path.abspath(profile_dir)}")
            chrome_options.add_argument("--profile-directory=Default")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                print("Driver criado com webdriver-manager!")
            except Exception:
                driver = webdriver.Chrome(options=chrome_options)
                print("Driver criado com driver do sistema!")
            
            # Anti-detecção
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.set_page_load_timeout(60)
            print("Driver configurado!")
            return driver
            
        except Exception as e:
            print(f"Erro ao criar driver: {e}")
            raise
    
    def login_gmail(self):
        """Login automático no Gmail"""
        print("Fazendo login no Gmail...")
        
        try:
            # Vai para Gmail
            self.driver.get("https://mail.google.com/mail/u/0/#inbox")
            time.sleep(3)
            
            # Verifica se já está logado
            try:
                self.driver.find_element(By.CSS_SELECTOR, "input[aria-label='Search mail'], input[aria-label='Pesquisar e-mails']")
                print("Ja logado no Gmail!")
                return True
            except:
                pass
            
            # Campo de email
            email_selectors = [
                "input[type='email']", "input[name='identifier']", "#identifierId",
                "input[aria-label*='email' i]", "input[autocomplete='username']"
            ]
            
            email_field = None
            for selector in email_selectors:
                try:
                    email_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"Campo de email encontrado: {selector}")
                    break
                except:
                    continue
            
            if not email_field:
                print("Campo de email nao encontrado")
                return False
            
            # Preenche email
            email_field.clear()
            email_field.send_keys(self.email)
            print("Email preenchido")
            
            # Clica em "Proximo"
            next_selectors = ["#identifierNext", "button[jsname='LgbsSe']", "button[type='submit']"]
            for selector in next_selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if button.is_displayed():
                        button.click()
                        print("Botao 'Proximo' clicado")
                        break
                except:
                    continue
            
            time.sleep(3)
            
            # Campo de senha
            password_selectors = [
                "input[type='password']", "input[name='password']", "#password",
                "input[aria-label*='password' i]", "input[autocomplete='current-password']"
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"Campo de senha encontrado: {selector}")
                    break
                except:
                    continue
            
            if not password_field:
                print("Campo de senha nao encontrado")
                return False
            
            # Preenche senha
            password_field.clear()
            password_field.send_keys(self.password)
            print("Senha preenchida")
            
            # Clica em "Entrar"
            signin_selectors = ["#passwordNext", "button[jsname='LgbsSe']", "button[type='submit']"]
            for selector in signin_selectors:
                try:
                    button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if button.is_displayed():
                        button.click()
                        print("Botao 'Entrar' clicado")
                        break
                except:
                    continue
            
            # Aguarda login com múltiplas tentativas
            print("Aguardando login...")
            for i in range(20):  # 20 tentativas de 2 segundos = 40 segundos
                try:
                    self.driver.find_element(By.CSS_SELECTOR, "input[aria-label='Search mail'], input[aria-label='Pesquisar e-mails']")
                    print("Login bem-sucedido!")
                    return True
                except:
                    time.sleep(2)
                    if i % 5 == 0:  # A cada 10 segundos
                        print(f"Aguardando login... ({i*2}s)")
            
            print("Login falhou - timeout")
            return False
                
        except Exception as e:
            print(f"Erro durante login: {e}")
            return False
    
    def buscar_recibos(self, days=30):
        """Busca recibos no Gmail"""
        print(f"Buscando recibos dos ultimos {days} dias...")
        
        try:
            # Campo de busca
            search_selectors = [
                "input[aria-label='Search mail']",
                "input[aria-label='Pesquisar e-mails']",
                "input[placeholder*='Search']",
                "input[placeholder*='Pesquisar']",
                "input[type='text'][role='searchbox']",
                "#gs_lc50 input",
                ".gb_1f input"
            ]
            
            search_field = None
            for selector in search_selectors:
                try:
                    search_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    print(f"Campo de busca encontrado: {selector}")
                    break
                except:
                    continue
            
            if not search_field:
                print("Campo de busca nao encontrado")
                return False
            
            # Monta query de busca
            after_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y/%m/%d")
            senders_query = " OR ".join([f"from:{s}" for s in self.ai_senders])
            subjects_query = " OR ".join([f"subject:{s}" for s in self.receipt_keywords])
            query = f"({senders_query} OR {subjects_query}) after:{after_date}"
            
            print(f"Query: {query}")
            search_field.clear()
            search_field.send_keys(query)
            search_field.submit()
            
            time.sleep(5)
            print("Busca executada!")
            return True
            
        except Exception as e:
            print(f"Erro na busca: {e}")
            return False
    
    def extrair_recibos(self, max_results=200):
        """Extrai dados dos recibos encontrados"""
        print("Extraindo dados dos recibos...")
        
        try:
            # Aguarda resultados carregarem
            time.sleep(3)
            
            # Encontra linhas de emails
            email_rows = self.driver.find_elements(By.CSS_SELECTOR, "tr.zA")
            print(f"Emails encontrados: {len(email_rows)}")
            
            receipts = []
            
            for i, row in enumerate(email_rows[:max_results]):
                try:
                    # Extrai dados básicos
                    sender_el = row.find_element(By.CSS_SELECTOR, ".yX.xY .yW span")
                    subject_el = row.find_element(By.CSS_SELECTOR, ".y6 span span")
                    date_el = row.find_element(By.CSS_SELECTOR, ".xW.xY span")
                    
                    sender = sender_el.get_attribute("email") or sender_el.text
                    subject = subject_el.get_attribute("title") or subject_el.text
                    date_txt = date_el.get_attribute("title") or date_el.text
                    
                    # Verifica se é recibo válido
                    if self._is_valid_receipt(sender, subject):
                        # Extrai valor e ID
                        amount = self._extract_amount(subject)
                        receipt_id = self._extract_receipt_id(subject)
                        
                        receipt = {
                            'sender': sender,
                            'subject': subject,
                            'date': date_txt,
                            'amount': amount,
                            'receipt_id': receipt_id
                        }
                        
                        receipts.append(receipt)
                        print(f"Recibo {len(receipts)}: {sender} | {subject[:50]}...")
                
                except Exception as e:
                    continue
            
            print(f"Total de recibos validos: {len(receipts)}")
            return receipts
            
        except Exception as e:
            print(f"Erro na extracao: {e}")
            return []
    
    def _is_valid_receipt(self, sender, subject):
        """Verifica se é um recibo válido"""
        # Verifica se é fornecedor de IA
        if not any(ai_sender in sender.lower() for ai_sender in self.ai_senders):
            return False
        
        # Verifica palavras-chave de recibo
        subject_lower = subject.lower()
        return any(keyword in subject_lower for keyword in self.receipt_keywords)
    
    def _extract_amount(self, text):
        """Extrai valor monetário do texto"""
        patterns = [
            r'(?:USD|US\$|\$|R\$|BRL|EUR|€)\s?(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)',
            r'(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)\s?(?:USD|US\$|\$|R\$|BRL|EUR|€)',
            r'Total[:\s]+(?:USD|US\$|\$|R\$|BRL|EUR|€)?\s?(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def _extract_receipt_id(self, text):
        """Extrai ID do recibo do texto"""
        patterns = [
            r'(?:inv|invoice|receipt|nf)[_\-\s:]*([A-Za-z0-9\-]+)',
            r'#([A-Za-z0-9\-]+)',
            r'ID[:\s]+([A-Za-z0-9\-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def executar(self, days=30, max_results=200, headless=False, profile_dir=None):
        """Executa o processo completo"""
        print("INICIANDO RECEIPT SCRAPER")
        print("=" * 50)
        
        try:
            # 1. Criar driver
            self.driver = self.criar_driver(headless, profile_dir)
            
            # 2. Login
            if not self.login_gmail():
                print("Falha no login. Encerrando.")
                return
            
            # 3. Buscar recibos
            if not self.buscar_recibos(days):
                print("Falha na busca. Encerrando.")
                return
            
            # 4. Extrair recibos
            receipts = self.extrair_recibos(max_results)
            
            # 5. Mostrar resultados
            print("\n" + "=" * 50)
            print("RESULTADOS ENCONTRADOS:")
            print("=" * 50)
            
            for i, receipt in enumerate(receipts[:10], 1):
                print(f"{i}. {receipt['sender']}")
                print(f"   {receipt['subject']}")
                print(f"   {receipt['date']}")
                if receipt['amount']:
                    print(f"   Valor: {receipt['amount']}")
                if receipt['receipt_id']:
                    print(f"   ID: {receipt['receipt_id']}")
                print()
            
            print(f"Total de recibos encontrados: {len(receipts)}")
            print("=" * 50)
            
        except Exception as e:
            print(f"Erro geral: {e}")
        
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass


def main():
    parser = argparse.ArgumentParser(description="Receipt Scraper - Login + Scraping")
    parser.add_argument("--days", type=int, default=30, help="Dias para buscar (padrao: 30)")
    parser.add_argument("--max", type=int, default=200, help="Maximo de recibos (padrao: 200)")
    parser.add_argument("--show", action="store_true", help="Rodar com janela visivel")
    parser.add_argument("--profile", default=".selenium_profile/gmail", help="Diretorio de perfil")
    args = parser.parse_args()

    scraper = ReceiptScraper()
    scraper.executar(
        days=args.days,
        max_results=args.max,
        headless=not args.show,
        profile_dir=args.profile
    )


if __name__ == "__main__":
    main()
