#!/usr/bin/env python3
"""
Receipt Scraper: Login Gmail + Web Scraping + Encaminhamento
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
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.common.keys import Keys


class ReceiptScraper:
    def __init__(self):
        self.driver = None
        self.email = "iazello@zello.tec.br"
        self.password = "@Zello2025"
        self.forward_to = "contasapagar@zello.tec.br"
        
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

        # Regex para extração
        self.MONEY_RE = re.compile(r"(?:(?:USD|US\$|\$|R\$|BRL|EUR|€)\s?)(\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?)")
        self.ID_RE = re.compile(r"(?:inv|invoice|receipt|nf)[_\-\s:]*([A-Za-z0-9\-]+)", re.I)

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
            
            # Clica em "Próximo"
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
            try:
                password_field.clear()
                password_field.send_keys(self.password)
                print("Senha preenchida")
            except ElementNotInteractableException:
                print("Senha nao interagivel. Conclua o login manualmente na janela aberta e pressione Enter aqui...")
                try:
                    input()
                except Exception:
                    pass
            
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
            
            # Aguarda login com múltiplas verificações
            print("Aguardando carregamento da caixa de entrada...")
            for _ in range(25):  # ~50s
                time.sleep(2)
                current_url = ""
                try:
                    current_url = self.driver.current_url or ""
                except Exception:
                    pass

                # Sinais de que o Gmail carregou
                selectors_to_check = [
                    "input[aria-label='Search mail']",
                    "input[aria-label='Pesquisar e-mails']",
                    "[gh='tm']",                 # toolbar
                    "div[role='navigation']",    # nav lateral
                    "div[gh='cm']",              # botão Escrever/Compose
                    "div[role='main']"
                ]
                loaded = False
                for sel in selectors_to_check:
                    try:
                        if self.driver.find_elements(By.CSS_SELECTOR, sel):
                            loaded = True
                            break
                    except Exception:
                        continue

                if loaded or ("mail.google.com/mail" in current_url):
                    # Garante que estamos na inbox
                    try:
                        if "mail.google.com/mail" not in current_url:
                            self.driver.get("https://mail.google.com/mail/u/0/#inbox")
                            time.sleep(2)
                    except Exception:
                        pass
                    print("Login bem-sucedido ou inbox carregada.")
                    return True

            print("Login falhou (timeout aguardando inbox)")
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
            
            # Query mínima por assunto (PT/EN)
            after_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y/%m/%d")
            keywords = [
                "subject:receipt", "subject:invoice", "subject:billing",
                "subject:recibo", "subject:fatura", "subject:cobrança", "subject:pagamento"
            ]
            query = f"({' OR '.join(keywords)}) after:{after_date}"
            
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

    def habilitar_atalhos_gmail(self):
        """Ativa 'Atalhos do teclado' nas configurações do Gmail se estiverem desligados."""
        print("Verificando/ativando atalhos do teclado do Gmail...")
        try:
            # Abre menu de configurações (engrenagem)
            gear_selectors = [
                "div[aria-label='Settings']",
                "div[aria-label='Configurações']",
                "div[aria-label*='config']",
                "div[aria-label*='definições']",
            ]
            gear_btn = None
            for sel in gear_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for b in buttons:
                        if b.is_displayed():
                            gear_btn = b
                            break
                    if gear_btn:
                        break
                except Exception:
                    continue
            if gear_btn:
                try:
                    gear_btn.click()
                    time.sleep(1)
                except Exception:
                    pass

            # Clicar em "Ver todas as configurações" / "See all settings"
            see_all_xpaths = [
                "//div[normalize-space()='See all settings']",
                "//div[normalize-space()='Ver todas as configurações']",
                "//span[normalize-space()='See all settings']/ancestor::div[@role='button']",
                "//span[normalize-space()='Ver todas as configurações']/ancestor::div[@role='button']",
            ]
            opened = False
            for xp in see_all_xpaths:
                try:
                    el = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, xp))
                    )
                    if el and el.is_displayed():
                        el.click()
                        opened = True
                        break
                except Exception:
                    continue
            if not opened:
                # Como fallback, navega diretamente para a página de config
                try:
                    self.driver.get("https://mail.google.com/mail/u/0/#settings/general")
                except Exception:
                    pass

            # Aguarda aba Geral
            time.sleep(2)

            # Seleciona "Atalhos do teclado: Ativados"
            radios_xp = [
                "//td[normalize-space()='Keyboard shortcuts:']/following::input[@type='radio' and (@value='on' or @value='1')][1]",
                "//td[normalize-space()='Atalhos do teclado:']/following::input[@type='radio' and (@value='on' or @value='1')][1]",
            ]
            turned_on = False
            for xp in radios_xp:
                try:
                    el = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, xp))
                    )
                    if el and el.is_displayed():
                        self.driver.execute_script("arguments[0].click();", el)
                        turned_on = True
                        break
                except Exception:
                    continue

            # Clicar em "Salvar alterações" / "Save Changes"
            save_xp = [
                "//button[normalize-space()='Save Changes']",
                "//button[normalize-space()='Salvar alterações']",
                "//input[@type='submit' and (@value='Save Changes' or @value='Salvar alterações')]",
            ]
            for xp in save_xp:
                try:
                    el = WebDriverWait(self.driver, 2).until(
                        EC.presence_of_element_located((By.XPATH, xp))
                    )
                    if el and el.is_displayed():
                        el.click()
                        break
                except Exception:
                    continue

            # Volta para inbox
            try:
                self.driver.get("https://mail.google.com/mail/u/0/#inbox")
                time.sleep(2)
            except Exception:
                pass
            print("Atalhos verificados/ativados.")
        except Exception as e:
            print(f"Falha ao ativar atalhos: {e}")
    
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
                    
                    # Verifica se título parece recibo (PT/EN) sem depender de remetente
                    subj_lower = subject.lower()
                    if any(k in subj_lower for k in [
                        "receipt", "invoice", "billing", "payment",
                        "recibo", "fatura", "cobrança", "pagamento"
                    ]):
                        # Abrir e encaminhar para contas a pagar
                        encaminhado = self._encaminhar_email(row)

                        receipt = {
                            'sender': sender,
                            'subject': subject,
                            'date': date_txt,
                            'forwarded': encaminhado
                        }
                        receipts.append(receipt)
                        print(f"Primeiro recibo encontrado: {sender} | {subject}")
                        break
                
                except Exception:
                    continue
            
            return receipts
            
        except Exception as e:
            print(f"Erro na extracao: {e}")
            return []

    def _encaminhar_email(self, row_el):
        """Abre o email e encaminha para contasapagar@zello.tec.br"""
        try:
            # Abre o email
            try:
                row_el.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", row_el)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='main']"))
            )

            # Garante foco em uma mensagem aberta
            try:
                msg_headers = self.driver.find_elements(By.CSS_SELECTOR, "div[role='main'] div[aria-label*='Mensagem']")
                if msg_headers:
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", msg_headers[0])
                    msg_headers[0].click()
            except Exception:
                pass

            # Tenta abrir o modo encaminhar
            if not self._abrir_encaminhar_ui():
                print("Nao foi possivel abrir o modo Encaminhar automaticamente.")
                print("Clique em 'Encaminhar/Forward' na janela do Gmail (vou aguardar até 60s)...")
                if not self._esperar_campo_para(timeout_seconds=60):
                    print("Campo 'Para' nao apareceu. Abortando encaminhamento.")
                    return False

            # Preenche destinatario
            if not self._preencher_destinatario("contasapagar@zello.tec.br"):
                print("Nao foi possivel preencher o destinatario")
                return False

            # Enviar
            if not self._clicar_enviar():
                print("Nao foi possivel enviar o encaminhamento")
                return False

            # Aguarda confirmacao basica
            time.sleep(3)
            print("Email encaminhado para contasapagar@zello.tec.br")
            return True
        except Exception as e:
            print(f"Falha ao encaminhar: {e}")
            return False

    def _abrir_encaminhar_ui(self):
        """Abre a UI de encaminhar via atalho ou menu."""
        # Tenta atalho de teclado 'f'
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.send_keys('f')
            if self._esperar_campo_para():
                return True
        except Exception:
            pass

        # Tenta atalho Shift+F
        try:
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.send_keys(Keys.SHIFT, 'f')
            if self._esperar_campo_para():
                return True
        except Exception:
            pass

        # Tenta via menu "Mais/More" na barra da mensagem (kebab)
        menu_selectors = [
            "div[aria-label='Mais']",
            "div[aria-label='More']",
            "div[aria-label*='Mais op']",
            "div[aria-label*='More options']",
            "div[role='button'][aria-label*='Mais']",
            "div[role='button'][aria-label*='More']",
            "div[role='button'][data-tooltip*='Mais']",
            "div[role='button'][data-tooltip*='More']",
            "div[aria-label*='Opções']",
        ]
        for sel in menu_selectors:
            try:
                menu_btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for btn in menu_btns:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
                        # item de menu Encaminhar/Forward
                        try:
                            xpath_options = [
                                "//div[@role='menuitem' and (contains(., 'Encaminhar') or contains(., 'Forward'))]",
                                "//div[@role='menuitem' and @command='msg.forward']",
                                "//div[@role='menuitem' and contains(@data-action, 'forward')]",
                                "//span[(normalize-space(.)='Encaminhar' or normalize-space(.)='Forward')]/ancestor::div[@role='menuitem']"
                            ]
                            item = None
                            for xp in xpath_options:
                                try:
                                    item = WebDriverWait(self.driver, 3).until(
                                        EC.presence_of_element_located((By.XPATH, xp))
                                    )
                                    if item:
                                        break
                                except Exception:
                                    continue
                            if item:
                                item.click()
                                if self._esperar_campo_para():
                                    return True
                        except Exception:
                            continue
            except Exception:
                continue

        # Tenta via menu de opcoes de resposta (seta ao lado do responder)
        reply_more_selectors = [
            "div[aria-label='Mais opções de resposta']",
            "div[aria-label='More reply options']",
            "div[role='button'][aria-label*='opções de resposta']",
            "div[role='button'][aria-label*='reply options']"
        ]
        for sel in reply_more_selectors:
            try:
                btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for b in btns:
                    if b.is_displayed():
                        b.click()
                        time.sleep(0.5)
                        try:
                            item = None
                            xpath_options = [
                                "//div[@role='menuitem' and (normalize-space(.)='Encaminhar' or normalize-space(.)='Forward')]",
                                "//div[@role='menuitem' and @command='msg.forward']",
                                "//div[@role='menuitem' and contains(@data-action, 'forward')]",
                            ]
                            for xp in xpath_options:
                                try:
                                    item = WebDriverWait(self.driver, 3).until(
                                        EC.presence_of_element_located((By.XPATH, xp))
                                    )
                                    if item:
                                        break
                                except Exception:
                                    continue
                            if item:
                                item.click()
                                if self._esperar_campo_para():
                                    return True
                        except Exception:
                            continue
            except Exception:
                continue

        # Tenta clicar diretamente em um botão/ação visível "Encaminhar/Forward" no corpo da mensagem
        try:
            direct_xpath_variants = [
                "//span[normalize-space(.)='Encaminhar']/ancestor::*[@role='button' or @role='link'][1]",
                "//span[normalize-space(.)='Forward']/ancestor::*[@role='button' or @role='link'][1]",
                "//*[@role='button' and .//span[normalize-space(.)='Encaminhar']]",
                "//*[@role='button' and .//span[normalize-space(.)='Forward']]",
                "//div[@role='button' and contains(@aria-label, 'Encaminhar')]",
                "//div[@role='button' and contains(@aria-label, 'Forward')]"
            ]
            for xp in direct_xpath_variants:
                try:
                    el = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.XPATH, xp))
                    )
                    if el and el.is_displayed():
                        el.click()
                        if self._esperar_campo_para():
                            return True
                except Exception:
                    continue
        except Exception:
            pass

        # Fallback final: varre o DOM por texto e clica no ancestral clicável
        try:
            clicked = self._click_by_visible_text_any(["Encaminhar", "Forward"])
            if clicked and self._esperar_campo_para():
                return True
        except Exception:
            pass
        return False

    def _click_by_visible_text_any(self, texts):
        """Procura elementos cujo innerText contenha qualquer texto alvo e clica no ancestral clicável."""
        js = """
        const targets = arguments[0];
        function isVisible(el){
          const r = el.getBoundingClientRect();
          return !!(r.width && r.height) && window.getComputedStyle(el).visibility !== 'hidden' && window.getComputedStyle(el).display !== 'none';
        }
        function findClickableAncestor(el){
          let cur = el;
          while (cur && cur !== document.body){
            const tag = cur.tagName.toLowerCase();
            const role = cur.getAttribute('role') || '';
            const aria = cur.getAttribute('aria-label') || '';
            const clickable = cur.onclick || cur.getAttribute('onclick') || cur.hasAttribute('role') || tag === 'button' || tag === 'a' || role.includes('button') || role.includes('link') || cur.hasAttribute('data-tooltip');
            if (clickable && isVisible(cur)) return cur;
            cur = cur.parentElement;
          }
          return null;
        }
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT, null);
        const candidates = [];
        while(walker.nextNode()){
          const el = walker.currentNode;
          if(!isVisible(el)) continue;
          const txt = (el.innerText || '').trim();
          if(!txt) continue;
          for(const t of targets){
            if(txt === t || txt.includes(t)){
              const clickable = findClickableAncestor(el);
              if(clickable){ candidates.push(clickable); break; }
            }
          }
        }
        if(candidates.length){ candidates[0].click(); return true; }
        return false;
        """
        try:
            return bool(self.driver.execute_script(js, texts))
        except Exception:
            return False

    def _esperar_campo_para(self, timeout_seconds=10):
        """Espera o campo 'Para/To' aparecer na janela de encaminhar."""
        try:
            # Seletores baseados no HTML real do Gmail
            selectors = [
                "input[peoplekit-id='BbVjBd']",  # Input real do campo Para
                "input[aria-label='Destinatários']",  # Aria-label do campo
                "input[role='combobox'][aria-label='Destinatários']",  # Combobox
                "textarea[name='to']",  # Fallback tradicional
                "input[aria-label='Para']",  # Fallback PT
                "input[aria-label='To']"  # Fallback EN
            ]
            
            for selector in selectors:
                try:
                    WebDriverWait(self.driver, timeout_seconds).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    print(f"Campo 'Para' encontrado com seletor: {selector}")
                    return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    def _preencher_destinatario(self, email):
        try:
            # Seletores baseados no HTML real do Gmail
            selectors = [
                "input[peoplekit-id='BbVjBd']",  # Input real do campo Para
                "input[aria-label='Destinatários']",  # Aria-label do campo
                "input[role='combobox'][aria-label='Destinatários']",  # Combobox
                "textarea[name='to']",  # Fallback tradicional
                "input[aria-label='Para']",  # Fallback PT
                "input[aria-label='To']"  # Fallback EN
            ]
            
            for sel in selectors:
                try:
                    el = self.driver.find_element(By.CSS_SELECTOR, sel)
                    if el.is_displayed():
                        print(f"Preenchendo campo com seletor: {sel}")
                        el.clear()
                        el.send_keys(email)
                        el.send_keys(Keys.ENTER)
                        print(f"Email '{email}' preenchido e Enter pressionado")
                        return True
                except Exception as e:
                    print(f"Falha com seletor {sel}: {e}")
                    continue
            return False
        except Exception as e:
            print(f"Erro geral ao preencher destinatário: {e}")
            return False

    def _clicar_enviar(self):
        try:
            send_selectors = [
                "div[aria-label='Send']",
                "div[aria-label='Enviar']",
                "div[role='button'][data-tooltip*='Send']",
                "div[role='button'][data-tooltip*='Enviar']"
            ]
            for sel in send_selectors:
                try:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for b in btns:
                        if b.is_displayed():
                            b.click()
                            return True
                except Exception:
                    continue
            # Fallback: Ctrl+Enter envia (atalho padrão do Gmail)
            try:
                body = self.driver.find_element(By.TAG_NAME, 'body')
                body.send_keys(Keys.CONTROL, Keys.ENTER)
                return True
            except Exception:
                return False
        except Exception:
            return False
    
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
            
            # 2. Login (se falhar, tenta seguir se a busca estiver visível)
            logged = self.login_gmail()
            if not logged:
                try:
                    self.driver.find_element(By.CSS_SELECTOR, "input[aria-label='Search mail'], input[aria-label='Pesquisar e-mails']")
                    print("Campo de busca visivel. Prosseguindo mesmo sem confirmar login.")
                except Exception:
                    print("Falha no login. Encerrando.")
                    return

            # 2.1 Habilitar atalhos do teclado (para permitir atalho 'f' de encaminhar)
            self.habilitar_atalhos_gmail()
            
            # 3. Buscar recibos
            if not self.buscar_recibos(days):
                print("Falha na busca. Encerrando.")
                return
            
            # 4. Extrair recibos (parar no primeiro encontrado)
            receipts = self.extrair_recibos(max_results)
            
            # 5. Mostrar resultados resumidos
            print("\n" + "=" * 50)
            print("RESULTADOS ENCONTRADOS:")
            print("=" * 50)
            
            for i, receipt in enumerate(receipts[:1], 1):
                print(f"{i}. {receipt['sender']}")
                print(f"   {receipt['subject']}")
                print(f"   {receipt['date']}")
                if receipt.get('amount'):
                    print(f"   Valor: {receipt['amount']}")
                if receipt.get('receipt_id'):
                    print(f"   ID: {receipt['receipt_id']}")
                print()
            
            print(f"Total de recibos encontrados (até parar): {len(receipts)}")
            print("=" * 50)
            
        except Exception as e:
            print(f"Erro geral: {e}")
        
        # Não fechar o Chrome automaticamente; manter janela aberta para próxima etapa
        # finally:
        #     if self.driver:
        #         try:
        #             self.driver.quit()
        #         except:
        #             pass


def main():
    parser = argparse.ArgumentParser(description="Receipt Scraper - Login + Scraping")
    parser.add_argument("--days", type=int, default=30, help="Dias para buscar (padrão: 30)")
    parser.add_argument("--max", type=int, default=200, help="Máximo de recibos (padrão: 200)")
    parser.add_argument("--show", action="store_true", help="Rodar com janela visível")
    parser.add_argument("--profile", default=".selenium_profile/gmail", help="Diretório de perfil")
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


