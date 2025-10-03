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
        
        # Blacklist
        self.blacklist_codigos = {
            'agora', 'caixa', 'otybg', 'state', 'learn', 'means', 'track', 'conta', 'goals', 
            'build', 'first', 'start', 'pages', 'pedro', 'silva', 'check', 'video', 'alert', 
            'coach', 'saber', 'sobre', 'novas', 'terms', 'about', 'these', 'manus', 'paste', 
            'tasks', 'ready', 'spent', 'power', 'moves', 'great', 'vamos', 'fazer', 'entre', 
            'leave', 'share', 'using', 'while', 'bring', 'ideas', 'looks', 'anexo', 'cloud', 
            'forum', 'prove', 'send', 'hours', 'known', 'could', 'later', 'gmail', 'google', 
            'email', 'https', 'mailto', 'portal', 'ativo', 'login', 'senha', 'codigo', 'hello', 'mundo'
        }
    
    def verificar_erro_credenciais(self):
        """Verifica se há mensagem de erro de credenciais na página"""
        try:
            erros_seletores = [
                ".MuiAlert-outlinedError",
                ".MuiAlert-root",
                "[role='alert']"
            ]
            
            for seletor in erros_seletores:
                try:
                    elementos_erro = self.driver_portal.find_elements(By.CSS_SELECTOR, seletor)
                    for elemento in elementos_erro:
                        if elemento.is_displayed():
                            texto_erro = elemento.text.lower()
                            palavras_erro = [
                                'incorreto', 
                                'incorretos',
                                'inválido',
                                'inválidos',
                                'erro',
                                'falha',
                                'impossível continuar',
                                'usuário ou código',
                                'acesso negado'
                            ]
                            
                            if any(palavra in texto_erro for palavra in palavras_erro):
                                print(f"\nERRO DETECTADO: {elemento.text}")
                                return True, elemento.text
                except Exception:
                    continue
            
            return False, None
        except Exception:
            return False, None
    
    def criar_driver(self, nome="driver"):
        """Cria driver otimizado"""
        chrome_options = Options()
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-images")
        chrome_options.add_argument("--disable-javascript-harmony-shipping")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.page_load_strategy = 'eager'
        
        temp_dir = tempfile.mkdtemp()
        chrome_options.add_argument(f"--user-data-dir={temp_dir}")
        chrome_options.add_argument("--profile-directory=Default")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        try:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
            except Exception:
                driver = webdriver.Chrome(options=chrome_options)
            
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            return driver
        except Exception as e:
            print(f"Erro: {e}")
            raise
    
    def etapa1_portal_email(self):
        """ETAPA 1: Portal + Email"""
        print("\nETAPA 1: PORTAL")
        
        try:
            self.driver_portal = self.criar_driver("Portal")
            self.driver_portal.get(self.url_portal)
            time.sleep(1)
            
            tem_erro, msg_erro = self.verificar_erro_credenciais()
            if tem_erro:
                raise Exception(f"Erro na página: {msg_erro}")
            
            wait = WebDriverWait(self.driver_portal, 10)
            
            email_selectors = [
                "input[type='email']", "input[name='email']", "input[id='email']",
                "#email", "input[name='usuario']", "input[name='login']"
            ]
            
            email_field = None
            for selector in email_selectors:
                try:
                    email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    break
                except Exception:
                    continue
            
            if not email_field:
                inputs = self.driver_portal.find_elements(By.TAG_NAME, "input")
                for input_field in inputs:
                    if input_field.get_attribute("type") in ["text", "email", None]:
                        email_field = input_field
                        break
            
            if email_field:
                email_field.clear()
                email_field.send_keys(self.email)
                self.clicar_botao_portal()
                time.sleep(1)
                
                tem_erro, msg_erro = self.verificar_erro_credenciais()
                if tem_erro:
                    raise Exception(f"Erro de credenciais: {msg_erro}")
                
                print("OK")
                return True
            return False
        except Exception as e:
            print(f"Erro: {e}")
            raise
    
    def clicar_botao_portal(self):
        """Clica botão"""
        for selector in ["button[type='submit']", ".btn-primary", "#submit"]:
            try:
                button = self.driver_portal.find_element(By.CSS_SELECTOR, selector)
                if button.is_displayed():
                    button.click()
                    return True
            except Exception:
                continue
        
        for xpath in ["//button[contains(text(), 'Continuar')]", "//button[contains(text(), 'Entrar')]"]:
            try:
                button = self.driver_portal.find_element(By.XPATH, xpath)
                if button.is_displayed():
                    button.click()
                    return True
            except Exception:
                continue
        return False
    
    def etapa2_gmail_codigo(self):
        """ETAPA 2: Gmail + Código"""
        print("\nETAPA 2: GMAIL")
        
        try:
            self.driver_gmail = self.criar_driver("Gmail")
            self.driver_gmail.get("https://mail.google.com")
            time.sleep(2)
            
            if self.fazer_login_gmail():
                if self.abrir_email_portal_automaticamente():
                    codigo = self.extrair_codigo_gmail()
                    if codigo:
                        print(f"Código: {codigo}")
                        return codigo
            return None
        except Exception as e:
            print(f"Erro: {e}")
            return None
    
    def abrir_email_portal_automaticamente(self):
        """Abre email"""
        time.sleep(1)
        
        try:
            elementos = self.driver_gmail.find_elements(By.CSS_SELECTOR, "span[email='autorizacao.portal@zello.tec.br']")
            if elementos:
                linha = elementos[0].find_element(By.XPATH, "./ancestor::tr[@role='row']")
                linha.click()
                time.sleep(1)
                return True
        except Exception:
            pass
        
        try:
            elementos = self.driver_gmail.find_elements(By.XPATH, "//span[contains(text(), 'Login - Portal Cliente')]")
            if elementos:
                linha = elementos[0].find_element(By.XPATH, "./ancestor::tr[@role='row']")
                linha.click()
                time.sleep(1)
                return True
        except Exception:
            pass
        
        return False
    
    def fazer_login_gmail(self):
        """Login Gmail"""
        try:
            wait = WebDriverWait(self.driver_gmail, 15)
            
            try:
                self.driver_gmail.find_element(By.CSS_SELECTOR, "[gh='tm']")
                return True
            except Exception:
                pass
            
            for seletor in ["#identifierId", "input[type='email']"]:
                try:
                    campo = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor)))
                    campo.clear()
                    campo.send_keys(self.email)
                    break
                except Exception:
                    continue
            
            self.clicar_botao_gmail("avancar")
            time.sleep(2)
            
            for seletor in ["input[type='password']", "#password"]:
                try:
                    campo = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, seletor)))
                    campo.clear()
                    campo.send_keys(self.senha)
                    break
                except Exception:
                    continue
            
            self.clicar_botao_gmail("senha")
            time.sleep(4)
            return True
        except Exception:
            return False
    
    def clicar_botao_gmail(self, tipo):
        """Clica botões Gmail"""
        seletor = "#identifierNext" if tipo == "avancar" else "#passwordNext"
        
        try:
            botao = self.driver_gmail.find_element(By.CSS_SELECTOR, seletor)
            if botao.is_displayed():
                botao.click()
                return True
        except Exception:
            pass
        
        try:
            botao = self.driver_gmail.find_element(By.XPATH, "//span[contains(text(), 'Avançar')]//parent::button")
            if botao.is_displayed():
                botao.click()
                return True
        except Exception:
            pass
        
        return False
    
    def extrair_codigo_gmail(self):
        """Extrai código"""
        codigo_encontrado = None
        
        for seletor in ["strong span[style*='font-size:22px']", "td strong span"]:
            try:
                elementos = self.driver_gmail.find_elements(By.CSS_SELECTOR, seletor)
                for elemento in elementos:
                    if elemento.is_displayed():
                        texto = elemento.text.strip()
                        if self.is_valid_code(texto):
                            codigo_encontrado = texto
                            break
                if codigo_encontrado:
                    break
            except Exception:
                continue
        
        if codigo_encontrado:
            try:
                self.driver_gmail.close()
            except Exception:
                pass
        
        return codigo_encontrado
    
    def is_valid_code(self, texto):
        """Verifica código"""
        if not texto or len(texto) < 4 or len(texto) > 8:
            return False
        if not re.match(r'^[a-zA-Z0-9]+$', texto):
            return False
        if texto.lower() in self.blacklist_codigos:
            return False
        return True
    
    def etapa3_portal_codigo(self, codigo):
        """ETAPA 3: Código - MELHORADO para não confundir com email"""
        print("\nETAPA 3: CÓDIGO")
        
        try:
            self.driver_portal.switch_to.window(self.driver_portal.window_handles[0])
            time.sleep(1)
            
            wait = WebDriverWait(self.driver_portal, 8)
            
            # Prioridade 1: Campos específicos de código
            selectors_codigo_priority = [
                "input[name='codigo']",
                "input[name='code']", 
                "input[name='verification_code']",
                "input[name='verificationCode']",
                "input[id='codigo']",
                "input[id='code']",
                "input[id='verification_code']",
                "input[placeholder*='código' i]",
                "input[placeholder*='code' i]",
                "input[placeholder*='verification' i]"
            ]
            
            codigo_field = None
            
            # Tentar seletores prioritários
            for selector in selectors_codigo_priority:
                try:
                    campo = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    if campo.is_displayed() and campo.is_enabled():
                        print(f"Campo encontrado (prioridade): {selector}")
                        codigo_field = campo
                        break
                except Exception:
                    continue
            
            # Se não encontrou, buscar manualmente mas COM FILTROS
            if not codigo_field:
                print("Buscando campo manualmente...")
                inputs = self.driver_portal.find_elements(By.TAG_NAME, "input")
                
                for input_field in inputs:
                    try:
                        # Obter atributos
                        input_type = input_field.get_attribute("type") or ""
                        input_name = (input_field.get_attribute("name") or "").lower()
                        input_id = (input_field.get_attribute("id") or "").lower()
                        input_value = input_field.get_attribute("value") or ""
                        input_placeholder = (input_field.get_attribute("placeholder") or "").lower()
                        
                        # FILTROS PARA EVITAR CAMPO DE EMAIL
                        
                        # 1. Ignorar se é tipo email
                        if input_type.lower() == "email":
                            continue
                        
                        # 2. Ignorar se name ou id contém "email", "mail", "usuario", "user"
                        palavras_email = ['email', 'mail', 'usuario', 'user', 'login', 'e-mail']
                        if any(palavra in input_name for palavra in palavras_email):
                            continue
                        if any(palavra in input_id for palavra in palavras_email):
                            continue
                        if any(palavra in input_placeholder for palavra in palavras_email):
                            continue
                        
                        # 3. Ignorar se já tem @ no valor (email preenchido)
                        if "@" in input_value:
                            continue
                        
                        # 4. Ignorar se o valor atual é igual ao email
                        if input_value == self.email:
                            continue
                        
                        # ACEITAR apenas campos que podem ser código
                        
                        # Aceitar se tipo é text, number, tel ou None
                        if input_type.lower() not in ["text", "number", "tel", ""]:
                            continue
                        
                        # Aceitar se está visível e habilitado
                        if not input_field.is_displayed() or not input_field.is_enabled():
                            continue
                        
                        # Preferir campos vazios ou com poucos caracteres
                        if len(input_value) <= 8:
                            print(f"Campo encontrado: name={input_name}, id={input_id}, type={input_type}")
                            codigo_field = input_field
                            break
                            
                    except Exception:
                        continue
            
            if codigo_field:
                print(f"Preenchendo código: {codigo}")
                
                # Limpar o campo de forma mais agressiva
                codigo_field.click()
                time.sleep(0.3)
                codigo_field.clear()
                time.sleep(0.2)
                
                # Tentar limpar com JavaScript se necessário
                try:
                    self.driver_portal.execute_script("arguments[0].value = '';", codigo_field)
                except:
                    pass
                
                # Preencher o código
                codigo_field.send_keys(codigo)
                time.sleep(0.3)
                
                # Verificar se foi preenchido corretamente
                valor_atual = codigo_field.get_attribute("value")
                print(f"Valor atual no campo: {valor_atual}")
                
                if valor_atual != codigo:
                    print("Tentando preencher novamente...")
                    codigo_field.clear()
                    time.sleep(0.2)
                    codigo_field.send_keys(codigo)
                
                # Clicar no botão de submit
                for selector in ["button[type='submit']", ".btn-primary", "#submit"]:
                    try:
                        button = self.driver_portal.find_element(By.CSS_SELECTOR, selector)
                        if button.is_displayed():
                            button.click()
                            break
                    except Exception:
                        continue
                
                time.sleep(1)
                
                # Verificar erro após enviar código
                tem_erro, msg_erro = self.verificar_erro_credenciais()
                if tem_erro:
                    raise Exception(f"Código incorreto: {msg_erro}")
                
                print("OK")
                return True
            else:
                print("ERRO: Campo de código não encontrado!")
                print("\nPor favor, envie o HTML do campo de código para melhorar a detecção.")
                return False
                
        except Exception as e:
            print(f"Erro: {e}")
            raise
    
    def etapa4_aprovacoes_financeiras(self):
        """ETAPA 4: Aprovações"""
        print("\nETAPA 4: APROVAÇÕES")
        
        try:
            time.sleep(2)
            wait = WebDriverWait(self.driver_portal, 10)
            
            xpaths = [
                "//button[contains(.,'Aprovações Financeiras')]",
                "//h6[contains(text(),'Aprovações Financeiras')]//ancestor::button"
            ]
            
            for xpath in xpaths:
                try:
                    botao = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    botao.click()
                    print("OK")
                    time.sleep(1)
                    return True
                except Exception:
                    continue
            return False
        except Exception:
            return False
    
    def etapa5_clicar_todos(self):
        """ETAPA 5: Todos"""
        print("\nETAPA 5: TODOS")
        
        try:
            time.sleep(1)
            wait = WebDriverWait(self.driver_portal, 10)
            
            for xpath in ["//div[contains(@class,'MuiSelect-select') and contains(text(),'Todos')]", "//div[@role='combobox']"]:
                try:
                    elemento = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    elemento.click()
                    print("OK")
                    time.sleep(1)
                    return True
                except Exception:
                    continue
            return False
        except Exception:
            return False
    
    def etapa6_aguardando_aprovacao(self):
        """ETAPA 6: Aguardando"""
        print("\nETAPA 6: AGUARDANDO")
        
        try:
            time.sleep(1)
            wait = WebDriverWait(self.driver_portal, 10)
            
            for xpath in ["//li[@data-value='aguardando']", "//li[contains(text(),'Aguardando Aprovação')]"]:
                try:
                    opcao = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    opcao.click()
                    print("OK")
                    time.sleep(1)
                    return True
                except Exception:
                    continue
            return False
        except Exception:
            return False
    
    def consultar_api_lancamento(self, codigo):
        """Consulta API"""
        try:
            headers = {
                "Authorization": self.api_token,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            payload = {"filtros": {"cd_lancamento": str(codigo)}}
            
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
    
    def normalizar_valor(self, valor_str):
        """Normaliza valor"""
        if not valor_str or valor_str == "N/A":
            return "0.00"
        
        valor = str(valor_str).replace("R$", "").replace(" ", "").replace("\xa0", "").strip()
        valor = valor.lstrip("-")
        
        if "," in valor:
            valor = valor.replace(".", "").replace(",", ".")
        
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
            
            codigo_portal = str(dados_portal['codigo'])
            codigo_api = str(api_data.get('cd_lancamento', ''))
            if codigo_portal != codigo_api:
                diferencas.append(f"Código: {codigo_portal}≠{codigo_api}")
            
            empresa_portal = dados_portal['empresa'].upper().strip()
            empresa_api = str(api_data.get('nome_completo', '')).upper().strip()
            if empresa_portal != empresa_api:
                diferencas.append("Empresa diferente")
            
            cnpj_portal = self.normalizar_cnpj(dados_portal['cnpj'])
            cnpj_api = self.normalizar_cnpj(api_data.get('cnpj_cpf', ''))
            if cnpj_portal != cnpj_api:
                diferencas.append(f"CNPJ: {cnpj_portal}≠{cnpj_api}")
            
            emissao_portal = self.normalizar_data(dados_portal['emissao'])
            emissao_api = self.normalizar_data(api_data.get('dt_emissao', ''))
            if emissao_portal != emissao_api:
                diferencas.append(f"Data: {emissao_portal}≠{emissao_api}")
            
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
        print("\nETAPA 7: COLETA")
        
        try:
            time.sleep(1)
            todos_lancamentos = []
            pagina = 1
            
            while True:
                print(f"Página {pagina}...")
                
                linhas = self.driver_portal.find_elements(By.CSS_SELECTOR, "tr.MuiTableRow-root.MuiTableRow-hover")
                
                for idx, linha in enumerate(linhas, 1):
                    try:
                        celulas = linha.find_elements(By.TAG_NAME, "td")
                        
                        if len(celulas) >= 7:
                            try:
                                codigo = celulas[0].find_element(By.CSS_SELECTOR, "h6").text.strip()
                            except:
                                codigo = "N/A"
                            
                            try:
                                empresa = celulas[1].find_element(By.CSS_SELECTOR, "h6").text.strip()
                            except:
                                empresa = "N/A"
                            
                            try:
                                cnpj = celulas[1].find_element(By.CSS_SELECTOR, "p").text.replace("CNPJ: ", "").strip()
                            except:
                                cnpj = "N/A"
                            
                            try:
                                emissao = celulas[2].find_element(By.CSS_SELECTOR, "p").text.strip()
                            except:
                                emissao = "N/A"
                            
                            try:
                                valor = celulas[6].find_element(By.CSS_SELECTOR, "h6").text.strip().replace('\xa0', ' ')
                            except:
                                valor = "N/A"
                            
                            lancamento = {
                                'codigo': codigo,
                                'empresa': empresa,
                                'cnpj': cnpj,
                                'emissao': emissao,
                                'valor': valor
                            }
                            
                            dados_api = self.consultar_api_lancamento(codigo)
                            
                            if dados_api:
                                correto, obs = self.comparar_dados(lancamento, dados_api)
                                lancamento['status'] = 'CORRETO' if correto else 'ERRADO'
                                lancamento['observacao'] = 'OK' if correto else ' | '.join(obs)
                            else:
                                lancamento['status'] = 'ERRO API'
                                lancamento['observacao'] = 'Sem resposta'
                            
                            todos_lancamentos.append(lancamento)
                            time.sleep(0.2)
                    except Exception:
                        continue
                
                try:
                    botao_proximo = self.driver_portal.find_element(By.CSS_SELECTOR, "button[aria-label='Go to next page']:not(.Mui-disabled)")
                    if botao_proximo.is_enabled():
                        botao_proximo.click()
                        time.sleep(1)
                        pagina += 1
                    else:
                        break
                except Exception:
                    break
            
            print(f"\nTotal: {len(todos_lancamentos)}")
            corretos = sum(1 for l in todos_lancamentos if l.get('status') == 'CORRETO')
            errados = sum(1 for l in todos_lancamentos if l.get('status') == 'ERRADO')
            print(f"Corretos: {corretos} | Errados: {errados}")
            
            salvar = input("Salvar CSV? (s/n): ").lower().strip()
            if salvar in ['s', 'sim', 'y']:
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
            caminho = os.path.join(pasta, f"lancamentos_{timestamp}.csv")
            
            with open(caminho, 'w', newline='', encoding='utf-8-sig') as arquivo:
                writer = csv.DictWriter(arquivo, fieldnames=['codigo', 'empresa', 'cnpj', 'emissao', 'valor', 'status', 'observacao'])
                writer.writeheader()
                for lanc in dados:
                    writer.writerow(lanc)
            
            return caminho
        except Exception:
            return None
    
    def fechar_drivers(self):
        """Fecha navegadores"""
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
    
    def mostrar_erro_visual(self, mensagem, tentativa):
        """Aviso visual"""
        print("\n╔" + "═"*68 + "╗")
        print("║" + "ERRO NA AUTOMAÇÃO".center(68) + "║")
        print("╠" + "═"*68 + "╣")
        print("║" + f"  Tentativa: {tentativa}/2".ljust(68) + "║")
        print("║" + f"  {mensagem[:60]}".ljust(68) + "║")
        print("╚" + "═"*68 + "╝\n")
    
    def mostrar_erro_final(self):
        """Erro final"""
        print("\n╔" + "═"*68 + "╗")
        print("║" + "AUTOMAÇÃO CANCELADA".center(68) + "║")
        print("╠" + "═"*68 + "╣")
        print("║  Falhou após 2 tentativas. Verifique conexão/credenciais. ║")
        print("╚" + "═"*68 + "╝\n")
    
    def executar_completo(self):
        """Execução COM RETRY"""
        for tentativa in range(1, 3):
            try:
                if tentativa > 1:
                    print(f"\nRETRY {tentativa}/2")
                    time.sleep(2)
                
                print("AUTOMAÇÃO RÁPIDA + DETECÇÃO INTELIGENTE")
                
                if not self.etapa1_portal_email():
                    raise Exception("Etapa 1 falhou")
                
                codigo = self.etapa2_gmail_codigo()
                if not codigo:
                    raise Exception("Etapa 2 falhou")
                
                if not self.etapa3_portal_codigo(codigo):
                    raise Exception("Etapa 3 falhou")
                
                if not self.etapa4_aprovacoes_financeiras():
                    raise Exception("Etapa 4 falhou")
                
                if not self.etapa5_clicar_todos():
                    raise Exception("Etapa 5 falhou")
                
                if not self.etapa6_aguardando_aprovacao():
                    raise Exception("Etapa 6 falhou")
                
                lancamentos = self.etapa7_coletar_e_comparar()
                
                print(f"\nSUCESSO! {len(lancamentos)} processados")
                return True
                
            except Exception as e:
                self.mostrar_erro_visual(str(e), tentativa)
                try:
                    self.fechar_drivers()
                except:
                    pass
                
                if tentativa == 2:
                    self.mostrar_erro_final()
                    return False
        
        return False


def main():
    print("AUTOMAÇÃO COMPLETA - VERSÃO OTIMIZADA")
    print("="*70)
    print("✓ Detecção de erros automática")
    print("✓ Não confunde campos de email/código")
    print("✓ Sistema de retry inteligente")
    print("✓ Velocidade otimizada")
    print("="*70)
    
    automacao = AutomacaoCompletaPortalGmail()
    
    try:
        input("\nEnter para iniciar: ")
        automacao.executar_completo()
        input("\nEnter para sair...")
    except KeyboardInterrupt:
        print("\nInterrompido")
    finally:
        try:
            automacao.fechar_drivers()
        except:
            pass


if __name__ == "__main__":
    main()