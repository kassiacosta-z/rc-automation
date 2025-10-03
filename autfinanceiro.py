import time
import re
import os
import csv
import tempfile
import requests
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


class AutomacaoCompletaPortalGmail:
    def __init__(self):
        """Automação completa: Login → Coleta → Comparação API"""
        self.driver_portal = None
        self.driver_gmail = None
        
        # Configurações Portal
        self.email = "iazello@zello.tec.br"
        self.senha = "@Zello2025"
        self.url_portal = "https://minhaareaonline.com.br/auth/empresa/login/66e34c1c1721cac4f4e72d78"
        
        # Configurações da API
        self.api_url = "https://zelloportais.cigam.cloud/RulesCGCentroSoft/WSCIGAMCRM.asmx/Zello_Lancamento_Pesquisa"
        self.api_token = "CG46H-JQR3C-2JRHY-XYRKY-GSPVM"
        
        # Blacklist para filtrar códigos falsos
        self.blacklist_codigos = {
            'agora', 'caixa', 'otybg', 'state', 'learn', 'means', 'track', 'conta', 'goals', 
            'build', 'first', 'start', 'pages', 'pedro', 'silva', 'check', 'video', 'alert', 
            'coach', 'saber', 'sobre', 'novas', 'terms', 'about', 'these', 'manus', 'paste', 
            'tasks', 'ready', 'spent', 'power', 'moves', 'great', 'vamos', 'fazer', 'entre', 
            'leave', 'share', 'using', 'while', 'bring', 'ideas', 'looks', 'anexo', 'cloud', 
            'forum', 'prove', 'send', 'hours', 'known', 'could', 'later', 'gmail', 'google', 
            'email', 'https', 'mailto', 'portal', 'ativo', 'login', 'senha', 'codigo', 'hello', 'mundo'
        }
    
    def criar_driver(self, nome="driver"):
        """Cria uma nova instância do Chrome driver em modo anônimo"""
        print(f"Criando {nome} em modo anônimo...")
        
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        
        temp_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        chrome_options.add_argument("--profile-directory=Default")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-component-extensions-with-background-pages")
        
        try:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                print(f"Driver {nome} criado com webdriver-manager!")
            except Exception:
                driver = webdriver.Chrome(options=chrome_options)
                print(f"Driver {nome} criado com driver do sistema!")
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print(f"Driver {nome} configurado em MODO ANÔNIMO!")
            return driver
            
        except Exception as e:
            print(f"Erro ao criar {nome}: {e}")
            raise
    
    def etapa1_portal_email(self):
        """ETAPA 1: Abrir portal e preencher email"""
        print("\n" + "="*60)
        print("ETAPA 1: ABRINDO PORTAL EM MODO ANÔNIMO")
        print("="*60)
        
        try:
            self.driver_portal = self.criar_driver("Driver Portal (Anônimo)")
            print(f"Abrindo portal: {self.url_portal}")
            self.driver_portal.get(self.url_portal)
            time.sleep(3)
            
            wait = WebDriverWait(self.driver_portal, 15)
            
            print("Procurando campo de email...")
            email_selectors = [
                "input[type='email']", "input[name='email']", "input[id='email']",
                "input[placeholder*='email' i]", "input[placeholder*='e-mail' i]",
                "#email", "input[name='usuario']", "input[name='login']"
            ]
            
            email_field = None
            for selector in email_selectors:
                try:
                    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    print(f"Campo de email encontrado: {selector}")
                    break
                except Exception:
                    continue
            
            if not email_field:
                print("Procurando qualquer campo de input...")
                inputs = self.driver_portal.find_elements(By.TAG_NAME, "input")
                for input_field in inputs:
                    input_type = input_field.get_attribute("type")
                    if input_type in ["text", "email", None]:
                        email_field = input_field
                        print(f"Campo encontrado - Type: {input_type}")
                        break
            
            if email_field:
                email_field.clear()
                email_field.send_keys(self.email)
                print(f"Email preenchido: {self.email}")
                self.clicar_botao_portal("continuar")
                print("ETAPA 1 CONCLUÍDA!")
                return True
            else:
                print("Campo de email não encontrado")
                return False
                
        except Exception as e:
            print(f"Erro na Etapa 1: {e}")
            return False
    
    def clicar_botao_portal(self, tipo="continuar"):
        """Clica em botão do portal"""
        print(f"Procurando botão de {tipo}...")
        
        button_selectors = [
            "button[type='submit']", "input[type='submit']",
            ".btn-primary", ".submit-btn", "#submit"
        ]
        
        for selector in button_selectors:
            try:
                button = self.driver_portal.find_element(By.CSS_SELECTOR, selector)
                if button.is_displayed():
                    self.driver_portal.execute_script("arguments[0].scrollIntoView();", button)
                    time.sleep(1)
                    button.click()
                    print(f"Botão clicado: {selector}")
                    return True
            except Exception:
                continue
        
        xpaths = [
            "//button[contains(text(), 'Continuar')]", "//button[contains(text(), 'Avançar')]",
            "//button[contains(text(), 'Entrar')]", "//button[contains(text(), 'Enviar')]",
            "//input[@value='Continuar']", "//input[@value='Avançar']"
        ]
        
        for xpath in xpaths:
            try:
                button = self.driver_portal.find_element(By.XPATH, xpath)
                if button.is_displayed():
                    self.driver_portal.execute_script("arguments[0].scrollIntoView();", button)
                    time.sleep(1)
                    button.click()
                    print("Botão clicado via XPath")
                    return True
            except Exception:
                continue
        
        try:
            buttons = self.driver_portal.find_elements(By.TAG_NAME, "button")
            if buttons:
                buttons[0].click()
                print("Primeiro botão clicado")
                return True
        except Exception:
            pass
        
        return False
    
    def etapa2_gmail_codigo(self):
        """ETAPA 2: Gmail + Login + Código"""
        print("\n" + "="*60)
        print("ETAPA 2: GMAIL + LOGIN + CÓDIGO")
        print("="*60)
        
        try:
            self.driver_gmail = self.criar_driver("Driver Gmail (Anônimo)")
            print("Abrindo Gmail...")
            self.driver_gmail.get("https://mail.google.com")
            time.sleep(5)
            
            if self.fazer_login_gmail():
                print("Login realizado!")
                
                if self.abrir_email_portal_automaticamente():
                    print("Email aberto automaticamente!")
                    codigo = self.extrair_codigo_gmail()
                    if codigo:
                        print(f"CÓDIGO COLETADO: {codigo}")
                        return codigo
                    else:
                        print("Código não encontrado")
                        return None
                else:
                    print("Abertura manual necessária")
                    print("Abra o email do Portal manualmente")
                    print("Pressione Enter...")
                    input()
                    codigo = self.extrair_codigo_gmail()
                    return codigo
            else:
                print("Modo manual")
                print("Faça login e abra o email")
                print("Pressione Enter...")
                input()
                codigo = self.extrair_codigo_gmail()
                return codigo
                
        except Exception as e:
            print(f"Erro na Etapa 2: {e}")
            return None
    
    def abrir_email_portal_automaticamente(self):
        """Abre email do portal automaticamente"""
        print("Procurando email do portal...")
        
        try:
            time.sleep(3)
            
            try:
                elementos_email = self.driver_gmail.find_elements(By.CSS_SELECTOR, "span[email='autorizacao.portal@zello.tec.br']")
                if elementos_email:
                    print(f"Encontrados {len(elementos_email)} emails")
                    elemento_email = elementos_email[0]
                    linha_email = elemento_email.find_element(By.XPATH, "./ancestor::tr[@role='row']")
                    print("Clicando no email...")
                    self.driver_gmail.execute_script("arguments[0].scrollIntoView();", linha_email)
                    time.sleep(1)
                    linha_email.click()
                    time.sleep(3)
                    print("Email aberto!")
                    return True
            except Exception as e:
                print(f"Método 1 falhou: {e}")
            
            try:
                print("Tentando método 2...")
                elementos_assunto = self.driver_gmail.find_elements(By.XPATH, 
                    "//span[contains(text(), 'Login - Portal Cliente')]")
                if elementos_assunto:
                    print(f"Encontrados {len(elementos_assunto)} emails")
                    elemento_assunto = elementos_assunto[0]
                    linha_email = elemento_assunto.find_element(By.XPATH, "./ancestor::tr[@role='row']")
                    print("Clicando...")
                    self.driver_gmail.execute_script("arguments[0].scrollIntoView();", linha_email)
                    time.sleep(1)
                    linha_email.click()
                    time.sleep(3)
                    print("Email aberto!")
                    return True
            except Exception as e:
                print(f"Método 2 falhou: {e}")
            
            return False
            
        except Exception as e:
            print(f"Erro: {e}")
            return False
    
    def fazer_login_gmail(self):
        """Login automático no Gmail"""
        print("Iniciando login...")
        
        try:
            wait = WebDriverWait(self.driver_gmail, 20)
            
            try:
                logado_elementos = ["[gh='tm']", "[role='main']", "table[role='grid']"]
                for seletor in logado_elementos:
                    try:
                        elemento = self.driver_gmail.find_element(By.CSS_SELECTOR, seletor)
                        if elemento.is_displayed():
                            print("Já logado!")
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            
            self.dispensar_popup_chrome()
            
            print("Campo email...")
            seletores_email = ["#identifierId", "input[type='email']", "input[name='identifier']"]
            
            campo_email = None
            for seletor in seletores_email:
                try:
                    campo_email = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor)))
                    print(f"Campo: {seletor}")
                    break
                except Exception:
                    continue
            
            if not campo_email:
                return False
            
            campo_email.clear()
            campo_email.send_keys(self.email)
            time.sleep(1)
            
            if not self.clicar_botao_gmail("avancar"):
                return False
            
            time.sleep(4)
            
            print("Campo senha...")
            seletores_senha = ["input[type='password']", "input[name='password']", "#password"]
            
            campo_senha = None
            for seletor in seletores_senha:
                try:
                    campo_senha = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor)))
                    print(f"Campo: {seletor}")
                    break
                except Exception:
                    continue
            
            if not campo_senha:
                return False
            
            campo_senha.clear()
            campo_senha.send_keys(self.senha)
            time.sleep(1)
            
            if not self.clicar_botao_gmail("senha"):
                return False
            
            time.sleep(8)
            
            try:
                wait.until(lambda driver: "mail.google.com" in driver.current_url and "signin" not in driver.current_url)
                print("Login OK!")
                return True
            except Exception:
                return True
                
        except Exception as e:
            print(f"Erro: {e}")
            return False
    
    def dispensar_popup_chrome(self):
        """Dispensa popup Chrome"""
        try:
            time.sleep(2)
            seletores = [
                "//button[contains(text(), 'Usar o Chrome sem uma conta')]",
                "//button[contains(text(), 'No thanks')]"
            ]
            
            for seletor in seletores:
                try:
                    botao = self.driver_gmail.find_element(By.XPATH, seletor)
                    if botao and botao.is_displayed():
                        botao.click()
                        time.sleep(2)
                        break
                except Exception:
                    continue
        except Exception:
            pass
    
    def clicar_botao_gmail(self, tipo="avancar"):
        """Clica botões do Gmail"""
        if tipo == "avancar":
            seletores = ["#identifierNext", ".VfPpkd-LgbsSe"]
            xpaths = ["//span[contains(text(), 'Avançar')]//parent::button"]
        elif tipo == "senha":
            seletores = ["#passwordNext", ".VfPpkd-LgbsSe"]
            xpaths = ["//span[contains(text(), 'Avançar')]//parent::button"]
        else:
            return False
        
        for seletor in seletores:
            try:
                botao = self.driver_gmail.find_element(By.CSS_SELECTOR, seletor)
                if botao.is_displayed() and botao.is_enabled():
                    botao.click()
                    return True
            except Exception:
                continue
        
        for xpath in xpaths:
            try:
                botao = self.driver_gmail.find_element(By.XPATH, xpath)
                if botao.is_displayed() and botao.is_enabled():
                    botao.click()
                    return True
            except Exception:
                continue
        
        return False
    
    def extrair_codigo_gmail(self):
        """Extrai código e fecha Gmail"""
        print("Extraindo código...")
        
        codigo_encontrado = None
        
        try:
            xpath = "/html/body/div[6]/div[3]/div/div[2]/div[4]/div/div/div/div[2]/div/div[1]/div/div[3]/div/div[2]/div[3]/div/div[3]/div[10]/div/div/div/div/div[1]/div[2]/div[3]/div[3]/div/table/tbody/tr[6]/td"
            elemento_td = self.driver_gmail.find_element(By.XPATH, xpath)
            codigo_span = elemento_td.find_element(By.XPATH, ".//strong/span[@style='font-size:22px']")
            codigo = codigo_span.text.strip()
            if self.is_valid_code(codigo):
                print(f"Código: {codigo}")
                codigo_encontrado = codigo
        except Exception:
            pass
        
        if not codigo_encontrado:
            seletores = [
                "strong span[style*='font-size:22px']",
                "table td[align='center'] strong span",
                "td strong span"
            ]
            
            for seletor in seletores:
                try:
                    elementos = self.driver_gmail.find_elements(By.CSS_SELECTOR, seletor)
                    for elemento in elementos:
                        if elemento.is_displayed():
                            texto = elemento.text.strip()
                            if self.is_valid_code(texto):
                                print(f"Código: {texto}")
                                codigo_encontrado = texto
                                break
                    if codigo_encontrado:
                        break
                except Exception:
                    continue
        
        if not codigo_encontrado:
            try:
                page_text = self.driver_gmail.find_element(By.TAG_NAME, "body").text
                padroes = [
                    r'\b[a-z]{2}[0-9][a-z]{2}\b',
                    r'\b[a-z]{5}\b',
                    r'\b[0-9]{5}\b'
                ]
                
                for padrao in padroes:
                    matches = re.findall(padrao, page_text, re.IGNORECASE)
                    for match in matches:
                        if self.is_valid_code(match):
                            print(f"Código: {match}")
                            codigo_encontrado = match
                            break
                    if codigo_encontrado:
                        break
            except Exception:
                pass
        
        if codigo_encontrado:
            print("Fechando Gmail...")
            try:
                self.driver_gmail.close()
                print("Gmail fechado!")
            except Exception as e:
                print(f"Erro ao fechar: {e}")
        
        return codigo_encontrado
    
    def is_valid_code(self, texto):
        """Verifica código válido"""
        if not texto or len(texto) < 4 or len(texto) > 8:
            return False
        if not re.match(r'^[a-zA-Z0-9]+$', texto):
            return False
        if texto.lower() in self.blacklist_codigos:
            return False
        return True
    
    def etapa3_portal_codigo(self, codigo):
        """ETAPA 3: Preencher código"""
        print("\n" + "="*60)
        print("ETAPA 3: PREENCHENDO CÓDIGO")
        print("="*60)
        
        try:
            self.driver_portal.switch_to.window(self.driver_portal.window_handles[0])
            time.sleep(1)
            
            print("Procurando campo...")
            selectors_codigo = [
                "input[name='codigo']", "input[name='code']",
                "input[name='verification_code']", "input[name='verificationCode']",
                "input[placeholder*='código' i]", "input[placeholder*='code' i]",
                "#codigo", "#code", "#verification_code"
            ]
            
            wait = WebDriverWait(self.driver_portal, 8)
            codigo_field = None
            
            for selector in selectors_codigo:
                try:
                    codigo_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    if codigo_field.is_displayed() and codigo_field.is_enabled():
                        print(f"Campo: {selector}")
                        break
                except Exception:
                    continue
            
            if not codigo_field:
                inputs = self.driver_portal.find_elements(By.TAG_NAME, "input")
                for input_field in inputs:
                    input_type = input_field.get_attribute("type")
                    input_name = input_field.get_attribute("name") or ""
                    input_value = input_field.get_attribute("value") or ""
                    
                    if (input_type in ["text", "number", None] and 
                        "email" not in input_name.lower() and
                        not input_value and 
                        "@" not in input_value and
                        input_field.is_displayed()):
                        
                        codigo_field = input_field
                        print(f"Campo: {input_name}")
                        break
            
            if codigo_field:
                print(f"CÓDIGO: {codigo}")
                codigo_field.click()
                codigo_field.clear()
                codigo_field.send_keys(codigo)
                
                valor_atual = codigo_field.get_attribute("value")
                if valor_atual != codigo:
                    codigo_field.clear()
                    codigo_field.send_keys(codigo)
                
                print("Enviando...")
                time.sleep(0.5)
                
                button_selectors = [
                    "button[type='submit']", "input[type='submit']",
                    ".btn-primary", "#submit"
                ]
                
                for selector in button_selectors:
                    try:
                        button = self.driver_portal.find_element(By.CSS_SELECTOR, selector)
                        if button.is_displayed() and button.is_enabled():
                            button.click()
                            print("Botão clicado!")
                            break
                    except Exception:
                        continue
                
                print("ETAPA 3 CONCLUÍDA!")
                return True
            else:
                print("Campo não encontrado!")
                return False
                
        except Exception as e:
            print(f"Erro: {e}")
            return False
    
    def etapa4_aprovacoes_financeiras(self):
        """ETAPA 4: Aprovações Financeiras"""
        print("\n" + "="*60)
        print("ETAPA 4: APROVAÇÕES FINANCEIRAS")
        print("="*60)
        
        try:
            time.sleep(5)
            
            xpaths = [
                "//button[contains(.,'Aprovações Financeiras')]",
                "//h6[contains(text(),'Aprovações Financeiras')]//ancestor::button"
            ]
            
            wait = WebDriverWait(self.driver_portal, 15)
            
            for xpath in xpaths:
                try:
                    botao = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    self.driver_portal.execute_script("arguments[0].scrollIntoView();", botao)
                    time.sleep(1)
                    botao.click()
                    print("Clicado!")
                    time.sleep(3)
                    return True
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            print(f"Erro: {e}")
            return False
    
    def etapa5_clicar_todos(self):
        """ETAPA 5: Clicar Todos"""
        print("\n" + "="*60)
        print("ETAPA 5: TODOS")
        print("="*60)
        
        try:
            time.sleep(3)
            
            xpaths = [
                "//div[contains(@class,'MuiSelect-select') and contains(text(),'Todos')]",
                "//div[@role='combobox']"
            ]
            
            wait = WebDriverWait(self.driver_portal, 15)
            
            for xpath in xpaths:
                try:
                    elemento = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    self.driver_portal.execute_script("arguments[0].scrollIntoView();", elemento)
                    time.sleep(1)
                    elemento.click()
                    print("Clicado!")
                    time.sleep(2)
                    return True
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            print(f"Erro: {e}")
            return False
    
    def etapa6_aguardando_aprovacao(self):
        """ETAPA 6: Aguardando Aprovação"""
        print("\n" + "="*60)
        print("ETAPA 6: AGUARDANDO APROVAÇÃO")
        print("="*60)
        
        try:
            time.sleep(2)
            
            xpaths = [
                "//li[@data-value='aguardando']",
                "//li[contains(text(),'Aguardando Aprovação')]"
            ]
            
            wait = WebDriverWait(self.driver_portal, 15)
            
            for xpath in xpaths:
                try:
                    opcao = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    self.driver_portal.execute_script("arguments[0].scrollIntoView();", opcao)
                    time.sleep(0.5)
                    opcao.click()
                    print("Selecionado!")
                    time.sleep(2)
                    return True
                except Exception:
                    continue
            
            return False
            
        except Exception as e:
            print(f"Erro: {e}")
            return False
    
    def consultar_api_lancamento(self, codigo):
        """Consulta API"""
        try:
            headers = {
                "Authorization": self.api_token,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            payload = {
                "filtros": {
                    "cd_lancamento": str(codigo)
                }
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception as e:
            print(f"Erro API: {e}")
            return None
    
    def normalizar_valor(self, valor_str):
        """Normaliza valor - Remove sinal negativo e formata corretamente"""
        if not valor_str or valor_str == "N/A":
            return "0.00"
        
        # Converter para string e limpar
        valor = str(valor_str).replace("R$", "").replace(" ", "").replace("\xa0", "").strip()
        
        # REMOVER SINAL NEGATIVO (API retorna valores negativos)
        valor = valor.lstrip("-")
        
        # Se tem vírgula, é formato brasileiro (ex: 17.603,34)
        if "," in valor:
            # Remove pontos de milhares e troca vírgula por ponto decimal
            valor = valor.replace(".", "").replace(",", ".")
        # Se não tem vírgula mas tem ponto, já está no formato correto (ex: 17603.34)
        
        try:
            return f"{float(valor):.2f}"
        except:
            return "0.00"
    
    def normalizar_data(self, data_str):
        """Normaliza data"""
        if not data_str or data_str == "N/A":
            return ""
        
        data = str(data_str).strip()
        
        if re.match(r'\d{2}/\d{2}/\d{4}', data):
            return data
        
        try:
            if re.match(r'\d{4}-\d{2}-\d{2}', data):
                partes = data.split('-')
                return f"{partes[2]}/{partes[1]}/{partes[0]}"
        except:
            pass
        
        return data
    
    def normalizar_cnpj(self, cnpj_str):
        """Normaliza CNPJ"""
        if not cnpj_str or cnpj_str == "N/A":
            return ""
        
        return re.sub(r'[^\d]', '', str(cnpj_str))
    
    def comparar_dados(self, dados_portal, dados_api):
        """Compara dados"""
        diferencas = []
        
        if not dados_api:
            return False, ["Não encontrado na API"]
        
        try:
            if isinstance(dados_api, list) and len(dados_api) > 0:
                api_data = dados_api[0]
            elif isinstance(dados_api, dict):
                if 'lancamentos' in dados_api and dados_api['lancamentos']:
                    api_data = dados_api['lancamentos'][0]
                elif 'd' in dados_api:
                    api_data = dados_api['d']
                    if isinstance(api_data, list) and len(api_data) > 0:
                        api_data = api_data[0]
                else:
                    api_data = dados_api
            else:
                return False, ["Formato inválido"]
            
            # CÓDIGO
            codigo_portal = str(dados_portal['codigo'])
            codigo_api = str(api_data.get('cd_lancamento', ''))
            if codigo_portal != codigo_api:
                diferencas.append(f"Código: {codigo_portal}≠{codigo_api}")
            
            # EMPRESA
            empresa_portal = dados_portal['empresa'].upper().strip()
            empresa_api = str(api_data.get('nome_completo', '')).upper().strip()
            if empresa_portal != empresa_api:
                diferencas.append("Empresa diferente")
            
            # CNPJ
            cnpj_portal = self.normalizar_cnpj(dados_portal['cnpj'])
            cnpj_api = self.normalizar_cnpj(api_data.get('cnpj_cpf', ''))
            if cnpj_portal != cnpj_api:
                diferencas.append(f"CNPJ: {cnpj_portal}≠{cnpj_api}")
            
            # EMISSÃO
            emissao_portal = self.normalizar_data(dados_portal['emissao'])
            emissao_api = self.normalizar_data(api_data.get('dt_emissao', ''))
            if emissao_portal != emissao_api:
                diferencas.append(f"Data: {emissao_portal}≠{emissao_api}")
            
            # VALOR - Remove sinal negativo da API
            valor_portal = self.normalizar_valor(dados_portal['valor'])
            valor_api = self.normalizar_valor(api_data.get('vl_saldo', ''))
            if valor_portal != valor_api:
                diferencas.append(f"Valor: {valor_portal}≠{valor_api}")
            
            if len(diferencas) == 0:
                return True, ["OK"]
            else:
                return False, diferencas
                
        except Exception as e:
            return False, [f"Erro: {str(e)}"]
    
    def etapa7_coletar_e_comparar(self):
        """ETAPA 7: Coleta + Comparação"""
        print("\n" + "="*60)
        print("ETAPA 7: COLETA + COMPARAÇÃO API")
        print("="*60)
        
        try:
            time.sleep(3)
            
            todos_lancamentos = []
            pagina_atual = 1
            
            while True:
                print(f"\nPágina {pagina_atual}...")
                
                linhas = self.driver_portal.find_elements(By.CSS_SELECTOR, "tr.MuiTableRow-root.MuiTableRow-hover")
                print(f"{len(linhas)} linhas")
                
                for idx, linha in enumerate(linhas, 1):
                    try:
                        celulas = linha.find_elements(By.TAG_NAME, "td")
                        
                        if len(celulas) >= 7:
                            try:
                                codigo = celulas[0].find_element(By.CSS_SELECTOR, "h6.MuiTypography-subtitle2").text.strip()
                            except:
                                codigo = "N/A"
                            
                            try:
                                empresa = celulas[1].find_element(By.CSS_SELECTOR, "h6.MuiTypography-h6").text.strip()
                            except:
                                empresa = "N/A"
                            
                            try:
                                cnpj_texto = celulas[1].find_element(By.CSS_SELECTOR, "p.MuiTypography-body2").text.strip()
                                cnpj = cnpj_texto.replace("CNPJ: ", "").strip()
                            except:
                                cnpj = "N/A"
                            
                            try:
                                emissao = celulas[2].find_element(By.CSS_SELECTOR, "p.MuiTypography-body2").text.strip()
                            except:
                                emissao = "N/A"
                            
                            try:
                                valor = celulas[6].find_element(By.CSS_SELECTOR, "h6.MuiTypography-h6").text.strip()
                                valor = valor.replace('\xa0', ' ')
                            except:
                                valor = "N/A"
                            
                            lancamento = {
                                'codigo': codigo,
                                'empresa': empresa,
                                'cnpj': cnpj,
                                'emissao': emissao,
                                'valor': valor
                            }
                            
                            print(f"  [{idx}] {codigo} - API...")
                            dados_api = self.consultar_api_lancamento(codigo)
                            
                            if dados_api:
                                correto, obs = self.comparar_dados(lancamento, dados_api)
                                if correto:
                                    lancamento['status'] = 'CORRETO'
                                    lancamento['observacao'] = 'OK'
                                    print(f"      CORRETO")
                                else:
                                    lancamento['status'] = 'ERRADO'
                                    lancamento['observacao'] = ' | '.join(obs)
                                    print(f"      ERRADO: {obs[0]}")
                            else:
                                lancamento['status'] = 'ERRO API'
                                lancamento['observacao'] = 'Sem resposta'
                                print(f"      ERRO API")
                            
                            todos_lancamentos.append(lancamento)
                            time.sleep(0.5)
                        
                    except Exception as e:
                        print(f"  Erro linha {idx}: {e}")
                        continue
                
                try:
                    botao_proximo = self.driver_portal.find_element(
                        By.CSS_SELECTOR, 
                        "button[aria-label='Go to next page']:not(.Mui-disabled)"
                    )
                    
                    if botao_proximo.is_enabled():
                        print("\nPróxima página...")
                        self.driver_portal.execute_script("arguments[0].scrollIntoView();", botao_proximo)
                        time.sleep(1)
                        botao_proximo.click()
                        time.sleep(3)
                        pagina_atual += 1
                    else:
                        break
                        
                except Exception:
                    print("\nÚltima página!")
                    break
            
            print("\n" + "="*60)
            print(f"CONCLUÍDO")
            print("="*60)
            print(f"Total: {len(todos_lancamentos)}")
            
            corretos = sum(1 for l in todos_lancamentos if l.get('status') == 'CORRETO')
            errados = sum(1 for l in todos_lancamentos if l.get('status') == 'ERRADO')
            erros = sum(1 for l in todos_lancamentos if l.get('status') == 'ERRO API')
            
            print(f"Corretos: {corretos}")
            print(f"Errados: {errados}")
            print(f"Erros API: {erros}")
            
            if errados > 0:
                print("\n" + "-"*60)
                print("DIVERGÊNCIAS:")
                for lanc in todos_lancamentos:
                    if lanc.get('status') == 'ERRADO':
                        print(f"\n{lanc['codigo']} - {lanc['empresa'][:40]}...")
                        print(f"{lanc['observacao']}")
            
            print("\n" + "-"*60)
            salvar = input("Salvar CSV? (s/n): ").lower().strip()
            
            if salvar in ['s', 'sim', 'yes', 'y']:
                caminho = self.salvar_csv(todos_lancamentos)
                if caminho:
                    print(f"Salvo: {caminho}")
            
            return todos_lancamentos
            
        except Exception as e:
            print(f"Erro: {e}")
            return []
    
    def salvar_csv(self, dados):
        """Salva CSV"""
        try:
            pasta = os.path.join(os.path.expanduser("~"), "Downloads")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome = f"lancamentos_{timestamp}.csv"
            caminho = os.path.join(pasta, nome)
            
            with open(caminho, 'w', newline='', encoding='utf-8-sig') as arquivo:
                campos = ['codigo', 'empresa', 'cnpj', 'emissao', 'valor', 'status', 'observacao']
                writer = csv.DictWriter(arquivo, fieldnames=campos)
                writer.writeheader()
                
                for lanc in dados:
                    writer.writerow(lanc)
            
            return caminho
            
        except Exception as e:
            print(f"Erro: {e}")
            return None
    
    def fechar_drivers(self):
        """Fecha navegadores"""
        print("Fechando...")
        
        if self.driver_gmail:
            try:
                if hasattr(self.driver_gmail, 'service') and self.driver_gmail.service.is_connectable():
                    self.driver_gmail.quit()
            except Exception:
                pass
        
        if self.driver_portal:
            try:
                self.driver_portal.quit()
            except Exception:
                pass
    
    def executar_completo(self):
        """Execução completa"""
        try:
            print("=" * 70)
            print("AUTOMAÇÃO COMPLETA - COLETA + COMPARAÇÃO")
            print("=" * 70)
            
            if not self.etapa1_portal_email():
                return False
            time.sleep(1)
            
            codigo = self.etapa2_gmail_codigo()
            if not codigo:
                return False
            
            if not self.etapa3_portal_codigo(codigo):
                return False
            time.sleep(1)
            
            if not self.etapa4_aprovacoes_financeiras():
                return False
            time.sleep(1)
            
            if not self.etapa5_clicar_todos():
                return False
            time.sleep(1)
            
            if not self.etapa6_aguardando_aprovacao():
                return False
            time.sleep(2)
            
            lancamentos = self.etapa7_coletar_e_comparar()
            
            print("\n" + "="*60)
            print("SUCESSO!")
            print(f"Processados: {len(lancamentos)}")
            print("="*60)
            
            return True
            
        except Exception as e:
            print(f"ERRO: {e}")
            return False
        
        finally:
            print("\nPressione Enter...")
            input()
            self.fechar_drivers()


def main():
    print("AUTOMAÇÃO COMPLETA")
    print("=" * 70)
    print("1-6. Login e navegação")
    print("7. Coleta + Comparação API")
    print("")
    
    automacao = AutomacaoCompletaPortalGmail()
    
    try:
        continuar = input("Enter para iniciar / 'q' sair: ")
        if continuar.lower() == 'q':
            return
        
        sucesso = automacao.executar_completo()
        
        if sucesso:
            print("\nCONCLUÍDO!")
        else:
            print("\nFinalizado com problemas.")
            
    except KeyboardInterrupt:
        print("\n\nInterrompido")
        try:
            automacao.fechar_drivers()
        except:
            pass
    except Exception as e:
        print(f"\nErro: {e}")
        try:
            automacao.fechar_drivers()
        except:
            pass


if __name__ == "__main__":
    main()