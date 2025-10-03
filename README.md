# RC Automation - Automação de Recibos de IA

Sistema automatizado para monitoramento e encaminhamento de recibos de provedores de IA (OpenAI, Anthropic, Cursor, etc.) via Gmail.

## 🚀 Funcionalidades

- **Monitoramento Automático**: Escaneia emails de `iazello@zello.tec.br` em busca de recibos
- **Detecção Inteligente**: Identifica recibos em português e inglês
- **Encaminhamento Automático**: Envia automaticamente para `contasapagar@zello.tec.br`
- **Interface Selenium**: Usa automação de navegador para contornar limitações da API
- **Seletores Robustos**: Múltiplos seletores CSS para máxima compatibilidade

## 📋 Pré-requisitos

- Python 3.8+
- Google Chrome
- Conta Gmail com acesso a `iazello@zello.tec.br`

## 🛠️ Instalação

```bash
# Clone o repositório
git clone https://github.com/kassiacosta-z/rc-automation.git
cd rc-automation

# Instale as dependências
pip install -r requirements.txt

# Configure as credenciais (opcional)
# Edite cli_selenium_scan.py com suas credenciais
```

## 🎯 Como Usar

### Execução Básica
```bash
python cli_selenium_scan.py
```

### Opções Avançadas
```bash
# Buscar últimos 30 dias, máximo 20 emails
python cli_selenium_scan.py --days 30 --max 20

# Modo debug (mostra navegador)
python cli_selenium_scan.py --show

# Buscar últimos 365 dias
python cli_selenium_scan.py --days 365 --max 50
```

## ⚙️ Configuração

### Credenciais
Edite o arquivo `cli_selenium_scan.py`:

```python
self.email = "iazello@zello.tec.br"  # Email de origem
self.password = "@Zello2025"         # Senha
self.forward_to = "contasapagar@zello.tec.br"  # Email de destino
```

### Provedores de IA Monitorados
- OpenAI (noreply@openai.com, billing@openai.com)
- Anthropic (receipts@anthropic.com)
- Cursor (billing@cursor.com)
- Stripe (invoice+statements+acct_*@stripe.com)

## 🔧 Arquitetura

### Estrutura do Projeto
```
rc-automation/
├── cli_selenium_scan.py    # Script principal
├── app.py                  # Interface web Flask
├── requirements.txt        # Dependências Python
├── Dockerfile             # Containerização
├── docker-compose.yml     # Orquestração
└── README.md              # Documentação
```

### Classes Principais
- **`ReceiptScraper`**: Classe principal para automação
- **`GmailService`**: Serviço de integração com Gmail
- **`ReceiptExtractor`**: Extração de dados dos recibos

## 🐳 Docker

```bash
# Build da imagem
docker build -t rc-automation .

# Executar container
docker run -it rc-automation

# Com docker-compose
docker-compose up
```

## 📊 Funcionamento

1. **Login**: Acessa Gmail via Selenium
2. **Busca**: Procura emails com palavras-chave de recibos
3. **Filtragem**: Identifica emails de provedores de IA
4. **Encaminhamento**: Abre interface de encaminhamento e envia
5. **Log**: Registra todas as operações

## 🔍 Troubleshooting

### Problemas Comuns

**Erro de Login**
- Verifique credenciais em `cli_selenium_scan.py`
- Complete login manualmente se necessário

**Campo "Para" não encontrado**
- Script usa múltiplos seletores CSS
- Atualizações do Gmail podem requerer ajustes

**Chrome não inicia**
- Instale Google Chrome
- Verifique permissões do sistema

## 📝 Logs

O sistema gera logs detalhados:
- Status de login
- Emails encontrados
- Processo de encaminhamento
- Erros e exceções

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## 👥 Autores

- **Kassia Costa** - *Desenvolvimento inicial* - [kassiacosta-z](https://github.com/kassiacosta-z)

## 📞 Suporte

Para suporte, abra uma issue no GitHub ou entre em contato via email.

---

**Status**: ✅ Funcional | **Versão**: 1.0.0 | **Última atualização**: Janeiro 2025