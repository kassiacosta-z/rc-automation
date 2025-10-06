# 📖 Manual do Usuário - RC Automation

## 🎯 Introdução

O **RC Automation** é um sistema automatizado que monitora sua conta Gmail em busca de recibos de provedores de IA e os encaminha automaticamente para o email de contas a pagar.

## 🚀 Início Rápido

### **1. Execução Básica**
```bash
python cli_selenium_scan.py
```

### **2. Com Debug (Recomendado)**
```bash
python cli_selenium_scan.py --show
```

### **3. Busca Completa**
```bash
python cli_selenium_scan.py --show --days 365 --max 50
```

## 📋 Pré-requisitos

### **Sistema**
- ✅ Windows 10/11
- ✅ Python 3.8+
- ✅ Google Chrome instalado
- ✅ Acesso à internet

### **Conta Gmail**
- ✅ Email: `iazello@zello.tec.br`
- ✅ Senha: `@Zello2025`
- ✅ Acesso liberado para automação

## 🎮 Como Usar

### **Passo 1: Abrir Terminal**
1. Pressione `Win + R`
2. Digite `cmd` ou `powershell`
3. Pressione Enter

### **Passo 2: Navegar para o Projeto**
```bash
cd C:\Users\User\workspace\automacao-recibos-ia
```

### **Passo 3: Executar o Sistema**
```bash
python cli_selenium_scan.py --show
```

### **Passo 4: Acompanhar o Processo**
O sistema irá:
1. 🔐 **Abrir Chrome e fazer login**
2. 🔍 **Buscar recibos de IA**
3. 📧 **Encaminhar para `contasapagar@zello.tec.br`**
4. ✅ **Mostrar resultados**

## 📊 O que Esperar

### **Tela de Login**
- Chrome abrirá automaticamente
- Login será preenchido automaticamente
- Se pedir verificação, complete manualmente

### **Processo de Busca**
```
🔍 Buscando recibos dos últimos 365 dias...
📧 Emails encontrados: 100
📋 Processando recibos...
```

### **Resultado Final**
```
✅ Email encaminhado para contasapagar@zello.tec.br
📊 Total de recibos encontrados: 1
```

## ⚙️ Opções Avançadas

### **Parâmetros Disponíveis**

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `--days` | Dias para buscar | `--days 30` |
| `--max` | Máximo de emails | `--max 20` |
| `--show` | Mostrar navegador | `--show` |
| `--profile` | Perfil específico | `--profile .selenium_profile/gmail` |

### **Exemplos de Uso**

```bash
# Buscar últimos 30 dias, máximo 20 emails
python cli_selenium_scan.py --days 30 --max 20

# Modo silencioso (sem janela)
python cli_selenium_scan.py --days 365 --max 50

# Com perfil específico
python cli_selenium_scan.py --profile .selenium_profile/gmail
```

## 🔍 Provedores Monitorados

O sistema monitora recibos de:

### **Provedores de IA**
- ✅ **OpenAI** (`noreply@openai.com`, `billing@openai.com`)
- ✅ **Anthropic** (`receipts@anthropic.com`, `billing@anthropic.com`)
- ✅ **Cursor** (`billing@cursor.com`)
- ✅ **Stripe** (`invoice+statements+acct_*@stripe.com`)
- ✅ **Paddle** (`help@paddle.com`)

### **Palavras-chave**
- **Português**: recibo, fatura, cobrança, pagamento, transação
- **Inglês**: receipt, invoice, billing, payment, transaction

## 🐛 Solução de Problemas

### **Problema 1: "Senha não interagível"**
```
Solução:
1. Complete o login manualmente na janela do Chrome
2. Pressione Enter no terminal
3. O sistema continuará automaticamente
```

### **Problema 2: "Chrome não inicia"**
```
Solução:
1. Instale Google Chrome
2. Verifique se não há outros processos Chrome
3. Execute como administrador se necessário
```

### **Problema 3: "Campo 'Para' não encontrado"**
```
Status: ✅ CORRIGIDO
O sistema usa seletores robustos que funcionam com a interface atual do Gmail
```

### **Problema 4: "Nenhum recibo encontrado"**
```
Possíveis causas:
1. Não há recibos no período especificado
2. Recibos não estão nos provedores monitorados
3. Query de busca muito restritiva

Solução:
1. Aumente o período: --days 365
2. Verifique se há recibos manualmente no Gmail
3. Execute com --show para ver o processo
```

## 📈 Interpretando Resultados

### **Log de Sucesso**
```
✅ Login bem-sucedido ou inbox carregada
✅ Atalhos verificados/ativados
✅ Emails encontrados: 100
✅ Campo 'Para' encontrado
✅ Email encaminhado para contasapagar@zello.tec.br
```

### **Informações do Recibo**
```
1. PBC, eu
   Your receipt from Anthropic, PBC #2392-9597-2984
   qua., 17 de set. de 2025, 12:06
```

### **Métricas**
- **Emails encontrados**: Total de emails na busca
- **Recibos processados**: Recibos efetivamente encaminhados
- **Taxa de sucesso**: Porcentagem de sucesso

## 🔒 Segurança

### **Credenciais**
- ✅ Senhas não são expostas em logs
- ✅ Perfil Chrome mantém sessão
- ✅ Dados sensíveis protegidos

### **Dados**
- ✅ Apenas dados necessários são processados
- ✅ Encaminhamento seguro via Gmail
- ✅ Logs limpos sem informações sensíveis

## 📞 Suporte

### **Contatos**
- **Desenvolvedor**: Kassia Costa
- **Email**: kassia.costa@zello.tec.br
- **Repositório**: https://github.com/kassiacosta-z/rc-automation

### **Logs de Erro**
Se encontrar problemas, copie os logs completos do terminal para análise.

### **FAQ**

**P: O sistema funciona em outros navegadores?**
R: Não, apenas Google Chrome é suportado.

**P: Posso alterar o email de destino?**
R: Sim, edite a linha `self.forward_to` no arquivo `cli_selenium_scan.py`.

**P: O sistema funciona 24/7?**
R: Não, é executado manualmente. Para automação contínua, configure agendamento.

**P: Posso processar múltiplos recibos?**
R: Atualmente processa apenas o primeiro encontrado. Múltiplos recibos estão em desenvolvimento.

## 🎯 Dicas de Uso

### **Melhores Práticas**
1. **Execute com `--show`** para acompanhar o processo
2. **Use `--days 365`** para busca completa
3. **Execute regularmente** para não acumular recibos
4. **Verifique os logs** para identificar problemas

### **Agendamento**
Para executar automaticamente, configure uma tarefa agendada no Windows:
```bash
# Exemplo de tarefa agendada
python C:\Users\User\workspace\automacao-recibos-ia\cli_selenium_scan.py --days 30 --max 20
```

### **Monitoramento**
- Execute pelo menos uma vez por semana
- Verifique se os recibos estão sendo encaminhados
- Monitore os logs para erros

---

**Manual atualizado em**: Janeiro 2025  
**Versão do sistema**: 1.0.0  
**Status**: ✅ **SISTEMA FUNCIONAL**
