"""
Serviço para extração de dados de recibos de diferentes provedores de IA.

Esta classe base fornece a estrutura fundamental para identificar e extrair
dados de recibos de emails de provedores de IA como OpenAI, Anthropic, Cursor, etc.
"""

import re
import time
import logging
from typing import Dict, Optional, List, Union, Tuple
from datetime import datetime


class ReceiptExtractor:
    """
    Classe base para extração de dados de recibos de provedores de IA.
    
    Suporta identificação automática de provedor e extração de dados
    estruturados de emails de recibos.
    """
    
    def __init__(self, timeout: float = 2.0):
        """
        Inicializa o extrator com configurações de provedores suportados.
        
        Args:
            timeout: Timeout em segundos para tentativas de seletores
        """
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # Dicionário de provedores de IA com seus remetentes
        self.ia_providers = {
            'OpenAI': [
                'noreply@openai.com',
                'billing@openai.com'
            ],
            'Anthropic': [
                'receipts@anthropic.com'
            ],
            'Cursor': [
                'billing@cursor.com'
            ],
            'Manus': [
                'invoice+statements+acct_1R15XBHkfKp4fCS9@stripe.com'
            ],
            'N8N': [
                'help@paddle.com'
            ]
        }
        
        # Padrões regex robustos para extração de dados
        self.patterns = {
            'currency_values': [
                r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $25.00, $1,234.56
                r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # R$ 25,00, R$ 1.234,56
                r'€\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',   # € 25.00, € 1,234.56
                r'USD\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # USD 25.00
                r'BRL\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',  # BRL 25,00
                r'EUR\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # EUR 25.00
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*USD',  # 25.00 USD
                r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*BRL',  # 25,00 BRL
                r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*EUR'   # 25.00 EUR
            ],
            'dates': [
                r'(\d{1,2}/\d{1,2}/\d{4})',  # 30/09/2025, 9/30/2025
                r'(\d{4}-\d{2}-\d{2})',      # 2025-09-30
                r'([A-Za-z]+ \d{1,2}, \d{4})',  # September 30, 2025
                r'(\d{1,2} [A-Za-z]+ \d{4})',  # 30 September 2025
                r'(\d{1,2}/\d{1,2}/\d{2})',  # 30/09/25
                r'(\d{4}/\d{2}/\d{2})',      # 2025/09/30
                r'(\d{1,2}-\d{1,2}-\d{4})',  # 30-09-2025
                r'(\d{4}\.\d{2}\.\d{2})'     # 2025.09.30
            ],
            'receipt_numbers': [
                r'inv[_-]?(\w+)',           # inv_123456, inv-789, inv123
                r'receipt[_-]?(\w+)',       # receipt-789, receipt_456
                r'#(\d+)',                  # #123456
                r'invoice[_-]?(\w+)',       # invoice_123, invoice-456
                r'recibo[_-]?(\w+)',        # recibo_123, recibo-456
                r'nf[_-]?(\w+)',            # nf_123, nf-456
                r'nota[_-]?(\w+)',          # nota_123, nota-456
                r'transaction[_-]?(\w+)',   # transaction_123
                r'order[_-]?(\w+)',         # order_123, order-456
                r'bill[_-]?(\w+)',          # bill_123, bill-456
                r'(\d{4,12})',              # 123456789 (apenas números)
                r'([A-Z0-9]{6,12})'         # ABC123DEF456 (códigos alfanuméricos)
            ]
        }
        
        # Blacklist de valores inválidos
        self.blacklist_values = {
            'currency': [
                '0.00', '0,00', '0', '00', '000', '0000',
                '1.00', '1,00', '1', '10', '100', '1000',
                'test', 'example', 'sample', 'demo'
            ],
            'dates': [
                '1900-01-01', '2000-01-01', '2020-01-01',
                '01/01/1900', '01/01/2000', '01/01/2020',
                'test', 'example', 'sample', 'demo'
            ],
            'receipt_numbers': [
                'test', 'example', 'sample', 'demo', '123', '1234',
                '0000', '00000', '000000', 'abc', 'def', 'xyz'
            ]
        }
        
        # Seletores CSS e XPath para diferentes layouts de email
        self.selectors = self._initialize_selectors()
    
    def _initialize_selectors(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Inicializa seletores CSS e XPath para diferentes elementos de email.
        
        Returns:
            Dicionário com seletores organizados por tipo de elemento
        """
        return {
            'amount': {
                'css': [
                    "span[contains(text(), 'Total')]",
                    ".amount", ".price", ".total", ".value",
                    "[data-testid='amount']", "[data-testid='total']",
                    ".invoice-amount", ".receipt-amount",
                    "td:contains('Total')", "td:contains('Amount')",
                    ".currency", ".money", ".cost"
                ],
                'xpath': [
                    "//span[contains(text(), 'Total')]",
                    "//span[contains(text(), 'Amount')]",
                    "//td[contains(text(), '$')]",
                    "//td[contains(text(), 'R$')]",
                    "//td[contains(text(), '€')]",
                    "//*[contains(@class, 'amount')]",
                    "//*[contains(@class, 'total')]",
                    "//*[contains(@class, 'price')]"
                ]
            },
            'date': {
                'css': [
                    "span[contains(text(), 'Date')]",
                    ".date", ".invoice-date", ".receipt-date",
                    "[data-testid='date']", "[data-testid='invoice-date']",
                    ".billing-date", ".issue-date",
                    "td:contains('Date')", "td:contains('Issued')"
                ],
                'xpath': [
                    "//span[contains(text(), 'Date')]",
                    "//span[contains(text(), 'Issued')]",
                    "//td[contains(text(), '/')]",
                    "//td[contains(text(), '-')]",
                    "//*[contains(@class, 'date')]",
                    "//*[contains(@class, 'invoice-date')]"
                ]
            },
            'receipt_number': {
                'css': [
                    "span[contains(text(), 'Invoice')]",
                    "span[contains(text(), 'Receipt')]",
                    ".invoice-number", ".receipt-number", ".invoice-id",
                    "[data-testid='invoice-number']", "[data-testid='receipt-id']",
                    ".transaction-id", ".order-number",
                    "td:contains('Invoice')", "td:contains('Receipt')"
                ],
                'xpath': [
                    "//span[contains(text(), 'Invoice')]",
                    "//span[contains(text(), 'Receipt')]",
                    "//td[contains(text(), '#')]",
                    "//td[contains(text(), 'inv_')]",
                    "//*[contains(@class, 'invoice-number')]",
                    "//*[contains(@class, 'receipt-number')]"
                ]
            },
            'service': {
                'css': [
                    "span[contains(text(), 'Service')]",
                    ".service", ".product", ".plan",
                    "[data-testid='service']", "[data-testid='product']",
                    ".subscription", ".billing-plan",
                    "td:contains('Service')", "td:contains('Product')"
                ],
                'xpath': [
                    "//span[contains(text(), 'Service')]",
                    "//span[contains(text(), 'Product')]",
                    "//td[contains(text(), 'API')]",
                    "//td[contains(text(), 'Usage')]",
                    "//*[contains(@class, 'service')]",
                    "//*[contains(@class, 'product')]"
                ]
            }
        }
    
    def get_multiple_selectors(self, element_type: str) -> Dict[str, List[str]]:
        """
        Retorna arrays de seletores CSS e XPath para um tipo de elemento.
        
        Args:
            element_type: Tipo do elemento ('amount', 'date', 'receipt_number', 'service')
            
        Returns:
            Dicionário com listas de seletores CSS e XPath
        """
        return self.selectors.get(element_type, {'css': [], 'xpath': []})
    
    def try_multiple_selectors(self, driver, element_type: str, 
                             custom_selectors: Optional[List[str]] = None) -> Tuple[Optional[any], str]:
        """
        Tenta cada seletor da lista até encontrar o elemento.
        
        Args:
            driver: Instância do WebDriver (Selenium)
            element_type: Tipo do elemento a ser encontrado
            custom_selectors: Lista opcional de seletores customizados
            
        Returns:
            Tupla com (elemento_encontrado, seletor_que_funcionou)
        """
        selectors = self.get_multiple_selectors(element_type)
        
        # Combina seletores padrão com customizados
        all_css_selectors = selectors.get('css', [])
        all_xpath_selectors = selectors.get('xpath', [])
        
        if custom_selectors:
            all_css_selectors = custom_selectors + all_css_selectors
        
        # Tenta seletores CSS primeiro
        for selector in all_css_selectors:
            try:
                element = driver.find_element("css selector", selector)
                if element and element.is_displayed():
                    self.logger.info(f"Elemento {element_type} encontrado com CSS: {selector}")
                    return element, f"css:{selector}"
            except Exception as e:
                self.logger.debug(f"CSS selector falhou: {selector} - {e}")
                continue
        
        # Tenta seletores XPath
        for selector in all_xpath_selectors:
            try:
                element = driver.find_element("xpath", selector)
                if element and element.is_displayed():
                    self.logger.info(f"Elemento {element_type} encontrado com XPath: {selector}")
                    return element, f"xpath:{selector}"
            except Exception as e:
                self.logger.debug(f"XPath selector falhou: {selector} - {e}")
                continue
        
        self.logger.warning(f"Nenhum seletor funcionou para {element_type}")
        return None, ""
    
    def try_selector_list(self, driver, selectors: List[str], 
                         selector_type: str = "css") -> Tuple[Optional[any], str]:
        """
        Tenta cada seletor de uma lista específica.
        
        Args:
            driver: Instância do WebDriver (Selenium)
            selectors: Lista de seletores para tentar
            selector_type: Tipo de seletor ('css' ou 'xpath')
            
        Returns:
            Tupla com (elemento_encontrado, seletor_que_funcionou)
        """
        for selector in selectors:
            try:
                start_time = time.time()
                element = driver.find_element(selector_type, selector)
                
                # Verifica se elemento está visível e dentro do timeout
                if element and element.is_displayed():
                    elapsed = time.time() - start_time
                    if elapsed <= self.timeout:
                        self.logger.info(f"Seletor {selector_type} funcionou: {selector} (tempo: {elapsed:.2f}s)")
                        return element, f"{selector_type}:{selector}"
                
            except Exception as e:
                self.logger.debug(f"Seletor {selector_type} falhou: {selector} - {e}")
                continue
        
        self.logger.warning(f"Nenhum seletor {selector_type} da lista funcionou")
        return None, ""
    
    def identify_provider(self, sender_email: str) -> Optional[str]:
        """
        Identifica o provedor de IA baseado no email do remetente.
        
        Args:
            sender_email: Email do remetente do recibo
            
        Returns:
            Nome do provedor identificado ou None se não encontrado
        """
        sender_email = sender_email.lower().strip()
        
        for provider, emails in self.ia_providers.items():
            for email in emails:
                if sender_email == email.lower():
                    return provider
        
        return None
    
    def extract_receipt_data(self, email_data: Dict) -> Dict:
        """
        Extrai dados estruturados de um email de recibo.
        
        Args:
            email_data: Dicionário com dados do email contendo:
                - 'sender': Email do remetente
                - 'subject': Assunto do email
                - 'body': Conteúdo do email
                
        Returns:
            Dicionário com dados extraídos do recibo:
            {
                'provedor': 'OpenAI',
                'valor': '$25.00', 
                'data': '2025-09-30',
                'numero_recibo': 'inv_123456',
                'servico': 'API Usage',
                'success': True
            }
        """
        try:
            # Identificar provedor
            provider = self.identify_provider(email_data.get('sender', ''))
            
            if not provider:
                return {
                    'provedor': 'Desconhecido',
                    'valor': None,
                    'data': None,
                    'numero_recibo': None,
                    'servico': None,
                    'success': False,
                    'error': 'Provedor não identificado'
                }
            
            # Extrair dados básicos
            subject = email_data.get('subject', '')
            body = email_data.get('body', '')
            
            # Extrair valor monetário
            currency_value = self._extract_currency_value(subject + ' ' + body)
            
            # Extrair data
            date_value = self._extract_date(subject + ' ' + body)
            
            # Extrair número do recibo
            receipt_number = self._extract_receipt_number(subject + ' ' + body)
            
            # Identificar serviço (básico)
            service = self._identify_service(subject, body, provider)
            
            return {
                'provedor': provider,
                'valor': currency_value,
                'data': date_value,
                'numero_recibo': receipt_number,
                'servico': service,
                'success': True
            }
            
        except Exception as e:
            return {
                'provedor': 'Erro',
                'valor': None,
                'data': None,
                'numero_recibo': None,
                'servico': None,
                'success': False,
                'error': str(e)
            }
    
    def extract_monetary_values(self, text: str) -> List[Dict[str, str]]:
        """
        Extrai valores monetários do texto com validação robusta.
        
        Args:
            text: Texto para extrair valores monetários
            
        Returns:
            Lista de dicionários com valores encontrados:
            [{'value': '25.00', 'currency': '$', 'formatted': '$25.00'}]
        """
        monetary_values = []
        
        for pattern in self.patterns['currency_values']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if self._is_valid_currency_value(match):
                    # Determinar moeda baseada no padrão
                    currency = self._extract_currency_symbol(pattern, match)
                    formatted_value = f"{currency}{match}"
                    
                    monetary_values.append({
                        'value': match,
                        'currency': currency,
                        'formatted': formatted_value
                    })
        
        return monetary_values
    
    def extract_dates(self, text: str) -> List[Dict[str, str]]:
        """
        Extrai datas do texto com validação robusta.
        
        Args:
            text: Texto para extrair datas
            
        Returns:
            Lista de dicionários com datas encontradas:
            [{'date': '2025-09-30', 'format': 'YYYY-MM-DD', 'formatted': '30/09/2025'}]
        """
        dates = []
        
        for pattern in self.patterns['dates']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if self._is_valid_date(match):
                    # Normalizar formato da data
                    normalized_date = self._normalize_date(match)
                    format_type = self._detect_date_format(match)
                    
                    dates.append({
                        'date': normalized_date,
                        'format': format_type,
                        'formatted': match
                    })
        
        return dates
    
    def extract_receipt_numbers(self, text: str) -> List[Dict[str, str]]:
        """
        Extrai números de recibo do texto com validação robusta.
        
        Args:
            text: Texto para extrair números de recibo
            
        Returns:
            Lista de dicionários com números encontrados:
            [{'number': '123456', 'type': 'invoice', 'formatted': 'inv_123456'}]
        """
        receipt_numbers = []
        
        for pattern in self.patterns['receipt_numbers']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if self._is_valid_receipt_number(match):
                    # Determinar tipo baseado no padrão
                    receipt_type = self._extract_receipt_type(pattern)
                    formatted_number = self._format_receipt_number(receipt_type, match)
                    
                    receipt_numbers.append({
                        'number': match,
                        'type': receipt_type,
                        'formatted': formatted_number
                    })
        
        return receipt_numbers
    
    def _extract_currency_value(self, text: str) -> Optional[str]:
        """Extrai valor monetário do texto (método legado)."""
        values = self.extract_monetary_values(text)
        if values:
            return values[0]['formatted']
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extrai data do texto (método legado)."""
        dates = self.extract_dates(text)
        if dates:
            return dates[0]['formatted']
        return None
    
    def _extract_receipt_number(self, text: str) -> Optional[str]:
        """Extrai número do recibo do texto (método legado)."""
        numbers = self.extract_receipt_numbers(text)
        if numbers:
            return numbers[0]['formatted']
        return None
    
    def _identify_service(self, subject: str, body: str, provider: str) -> str:
        """
        Identifica o tipo de serviço baseado no provedor e conteúdo.
        
        Args:
            subject: Assunto do email
            body: Conteúdo do email
            provider: Provedor identificado
            
        Returns:
            Nome do serviço identificado
        """
        text = (subject + ' ' + body).lower()
        
        # Mapeamento básico de serviços por provedor
        service_mapping = {
            'OpenAI': 'API Usage',
            'Anthropic': 'Claude API',
            'Cursor': 'Cursor Pro',
            'Manus': 'Manus Platform',
            'N8N': 'N8N Cloud'
        }
        
        # Retorna serviço padrão do provedor
        return service_mapping.get(provider, 'Serviço de IA')
    
    def get_supported_providers(self) -> List[str]:
        """
        Retorna lista de provedores suportados.
        
        Returns:
            Lista com nomes dos provedores suportados
        """
        return list(self.ia_providers.keys())
    
    def get_provider_emails(self, provider: str) -> List[str]:
        """
        Retorna emails de um provedor específico.
        
        Args:
            provider: Nome do provedor
            
        Returns:
            Lista de emails do provedor ou lista vazia se não encontrado
        """
        return self.ia_providers.get(provider, [])
    
    def _is_valid_currency_value(self, value: str) -> bool:
        """
        Valida se um valor monetário é válido.
        
        Args:
            value: Valor a ser validado
            
        Returns:
            True se válido, False caso contrário
        """
        if not value or value.strip() == '':
            return False
        
        # Verificar blacklist
        if value.lower() in [v.lower() for v in self.blacklist_values['currency']]:
            return False
        
        # Verificar se é um número válido
        try:
            # Remover vírgulas e pontos para validação
            clean_value = value.replace(',', '').replace('.', '')
            if not clean_value.isdigit():
                return False
            
            # Verificar range (entre 0.01 e 999999.99)
            numeric_value = float(value.replace(',', '.'))
            return 0.01 <= numeric_value <= 999999.99
        except (ValueError, TypeError):
            return False
    
    def _is_valid_date(self, date_str: str) -> bool:
        """
        Valida se uma data é válida.
        
        Args:
            date_str: Data a ser validada
            
        Returns:
            True se válida, False caso contrário
        """
        if not date_str or date_str.strip() == '':
            return False
        
        # Verificar blacklist
        if date_str.lower() in [d.lower() for d in self.blacklist_values['dates']]:
            return False
        
        try:
            # Tentar parsear a data
            parsed_date = self._parse_date(date_str)
            if not parsed_date:
                return False
            
            # Verificar se está em range válido (2000-2030)
            year = parsed_date.year
            return 2000 <= year <= 2030
        except (ValueError, TypeError):
            return False
    
    def _is_valid_receipt_number(self, number: str) -> bool:
        """
        Valida se um número de recibo é válido.
        
        Args:
            number: Número a ser validado
            
        Returns:
            True se válido, False caso contrário
        """
        if not number or number.strip() == '':
            return False
        
        # Verificar blacklist
        if number.lower() in [n.lower() for n in self.blacklist_values['receipt_numbers']]:
            return False
        
        # Verificar comprimento mínimo
        if len(number) < 3:
            return False
        
        # Verificar se contém pelo menos um dígito
        if not re.search(r'\d', number):
            return False
        
        return True
    
    def _extract_currency_symbol(self, pattern: str, value: str) -> str:
        """
        Extrai símbolo da moeda baseado no padrão regex.
        
        Args:
            pattern: Padrão regex usado
            value: Valor extraído
            
        Returns:
            Símbolo da moeda
        """
        if '$' in pattern and 'R$' not in pattern:
            return '$'
        elif 'R$' in pattern:
            return 'R$'
        elif '€' in pattern:
            return '€'
        elif 'USD' in pattern:
            return 'USD'
        elif 'BRL' in pattern:
            return 'BRL'
        elif 'EUR' in pattern:
            return 'EUR'
        else:
            return '$'  # Default
    
    def _normalize_date(self, date_str: str) -> str:
        """
        Normaliza data para formato YYYY-MM-DD.
        
        Args:
            date_str: Data em formato original
            
        Returns:
            Data normalizada em YYYY-MM-DD
        """
        try:
            parsed_date = self._parse_date(date_str)
            if parsed_date:
                return parsed_date.strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            pass
        return date_str
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Faz parse de uma data em diferentes formatos.
        
        Args:
            date_str: Data em formato string
            
        Returns:
            Objeto datetime ou None se inválida
        """
        date_formats = [
            '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%Y/%m/%d',
            '%d-%m-%Y', '%m-%d-%Y', '%Y.%m.%d',
            '%d/%m/%y', '%m/%d/%y', '%y-%m-%d',
            '%B %d, %Y', '%d %B %Y',  # September 30, 2025
            '%b %d, %Y', '%d %b %Y'   # Sep 30, 2025
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _detect_date_format(self, date_str: str) -> str:
        """
        Detecta o formato da data.
        
        Args:
            date_str: Data em formato string
            
        Returns:
            Tipo de formato detectado
        """
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            return 'YYYY-MM-DD'
        elif re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_str):
            return 'DD/MM/YYYY'
        elif re.match(r'\d{1,2}/\d{1,2}/\d{2}', date_str):
            return 'DD/MM/YY'
        elif re.match(r'[A-Za-z]+ \d{1,2}, \d{4}', date_str):
            return 'Month DD, YYYY'
        elif re.match(r'\d{1,2} [A-Za-z]+ \d{4}', date_str):
            return 'DD Month YYYY'
        else:
            return 'Unknown'
    
    def _extract_receipt_type(self, pattern: str) -> str:
        """
        Extrai tipo do recibo baseado no padrão regex.
        
        Args:
            pattern: Padrão regex usado
            
        Returns:
            Tipo do recibo
        """
        if 'inv' in pattern:
            return 'invoice'
        elif 'receipt' in pattern:
            return 'receipt'
        elif 'recibo' in pattern:
            return 'recibo'
        elif 'nf' in pattern:
            return 'nota_fiscal'
        elif 'nota' in pattern:
            return 'nota'
        elif 'transaction' in pattern:
            return 'transaction'
        elif 'order' in pattern:
            return 'order'
        elif 'bill' in pattern:
            return 'bill'
        else:
            return 'unknown'
    
    def _format_receipt_number(self, receipt_type: str, number: str) -> str:
        """
        Formata número do recibo com prefixo apropriado.
        
        Args:
            receipt_type: Tipo do recibo
            number: Número do recibo
            
        Returns:
            Número formatado
        """
        if receipt_type == 'invoice':
            return f"inv_{number}"
        elif receipt_type == 'receipt':
            return f"receipt_{number}"
        elif receipt_type == 'recibo':
            return f"recibo_{number}"
        elif receipt_type == 'nota_fiscal':
            return f"nf_{number}"
        elif receipt_type == 'nota':
            return f"nota_{number}"
        elif receipt_type == 'transaction':
            return f"tx_{number}"
        elif receipt_type == 'order':
            return f"order_{number}"
        elif receipt_type == 'bill':
            return f"bill_{number}"
        else:
            return f"#{number}"
