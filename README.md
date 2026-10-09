# 📊 Gestor de Clientes & Cobranças Automáticas via WhatsApp Web

Aplicação desktop para **gestão de clientes, controle financeiro e
inadimplência**, com persistência local em SQLite e automação de cobranças
personalizadas pelo WhatsApp Web.

O sistema foi desenvolvido para funcionar localmente em computadores Windows,
sem a necessidade de instalar ou manter um servidor de banco de dados.

> **Atenção:** o envio pelo WhatsApp Web depende de uma sessão autenticada no
> navegador. A automação de teclado também exige que o navegador permaneça
> disponível e em foco durante o processamento. Use os disparos de forma
> responsável e respeite as políticas do WhatsApp.

## ✨ Funcionalidades principais

- **Interface moderna em CustomTkinter**
  - Janela desktop com tema escuro.
  - Navegação em abas:
    - 👤 **Cliente**: cadastro, edição e dados de cobrança.
    - ⚙️ **Configurações**: empresa, chave PIX e banco/favorecido.
- **Cadastro e edição de clientes**
  - Validação de nome, telefone, valor e dia de vencimento.
  - Sanitização automática de telefones com código do Brasil (`55`).
  - Máscara de valores em reais (`R$`), aceitando vírgula ou ponto.
  - Máscara de datas atrasadas no formato `DD/MM/AAAA`.
  - Cadastro de várias datas históricas separadas por vírgula.
- **Gestão de mensalidades**
  - Histórico individual por cliente.
  - Controle dos status `Pendente`, `Atrasado` e `Pago`.
  - Modal de baixa parcial/individual com caixas de seleção.
  - Registro da data de pagamento.
  - Atualização automática do status geral do cliente.
- **Cobranças pelo WhatsApp Web**
  - Mensagens personalizadas com nome do cliente, empresa, meses em aberto,
    valor total e dados do PIX.
  - URL do WhatsApp Web codificada com `urllib.parse.quote`.
  - Busca dinâmica por Google Chrome, Microsoft Edge ou Mozilla Firefox.
  - Pressionamento automático de `Enter` para enviar a mensagem.
  - Fechamento opcional da aba após o envio.
- **Disparo manual e automático**
  - O disparo manual permite à empresa enviar cobranças imediatamente para os
    clientes em aberto.
  - A rotina automática aplica a regra de pelo menos 3 dias de atraso e
    carência de 2 dias entre envios.
- **Intervalo entre envios**
  - O processamento ocorre em uma thread separada para manter a interface
    responsiva.
  - Entre clientes, é aplicado um intervalo aleatório de 25 a 45 segundos.
- **Persistência local**
  - Banco SQLite criado automaticamente como `clientes.db`.
  - Queries parametrizadas para operações de dados.
  - Criação e migração automática das tabelas necessárias.

## 🧰 Tecnologias utilizadas

- **Python 3.11+**
- **CustomTkinter** — interface gráfica.
- **SQLite3** — banco de dados local incluído no Python.
- **PyAutoGUI** — automação de teclado e mouse.
- **Webbrowser** — fallback para o navegador padrão do sistema.
- **Urllib** — codificação segura da mensagem na URL do WhatsApp Web.
- **Threading** — execução das cobranças sem congelar a interface.

## 🚀 Como executar localmente

### 1. Clonar o repositório

No PowerShell:

```powershell
git clone https://github.com/Marcio-12/Gestor.git
cd Gestor
```

### 2. Criar o ambiente virtual

```powershell
py -3.11 -m venv .venv
```

Caso o comando `py` não esteja disponível, use:

```powershell
python -m venv .venv
```

### 3. Ativar o ambiente virtual

No Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

No Prompt de Comando:

```bat
.\.venv\Scripts\activate.bat
```

Se o PowerShell bloquear scripts, execute a política apenas para o usuário
atual e tente novamente:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 4. Instalar as dependências

Usando o arquivo de dependências:

```powershell
python -m pip install -r requirements.txt
```

Ou instalando os pacotes essenciais diretamente:

```powershell
python -m pip install customtkinter pyautogui
```

O módulo `sqlite3`, `webbrowser`, `urllib` e `threading` fazem parte da
biblioteca padrão do Python e não precisam ser instalados separadamente.

### 5. Executar a aplicação

```powershell
python app.py
```

Na primeira execução, o sistema cria automaticamente o arquivo `clientes.db`
na pasta do projeto e prepara as tabelas `clientes`, `mensalidades` e
`configuracoes`.

## 🧭 Fluxo básico de uso

1. Abra a aba **⚙️ Configurações**.
2. Cadastre o nome da empresa, a chave PIX e, opcionalmente, o banco/favorecido.
3. Abra a aba **👤 Cliente**.
4. Informe nome, telefone, valor e dia de vencimento.
5. Se necessário, informe datas históricas no campo de inadimplência, por
   exemplo:

   ```text
   10/07/2026, 10/08/2026, 10/09/2026
   ```

6. Cadastre o cliente.
7. Use **✏️ Editar** para alterar dados ou histórico de mensalidades.
8. Use **✅ Marcar Pago** para selecionar individualmente as parcelas pagas.
9. Use **🚀 Disparar Cobranças (WhatsApp)** para iniciar o processamento.

Antes do disparo, mantenha o navegador aberto, autenticado no WhatsApp Web e
evite utilizar o teclado ou mouse durante a automação de cada envio.

## 📁 Estrutura de arquivos

| Arquivo | Responsabilidade |
| --- | --- |
| [`app.py`](./app.py) | Interface gráfica CustomTkinter, abas, formulários, tabela, modais, validações visuais e execução das cobranças em thread. |
| [`gestor.py`](./gestor.py) | Regras de negócio, validações de backend, operações SQLite, mensalidades, geração das mensagens e automação do WhatsApp Web. |
| [`requirements.txt`](./requirements.txt) | Lista de dependências Python utilizadas pelo projeto. |
| `clientes.db` | Banco SQLite local criado automaticamente. Não deve ser versionado. |
| [`redme/README.md`](./redme/README.md) | Documentação legada da versão inicial em modo terminal. |

## 🗃️ Banco de dados

O arquivo `clientes.db` contém principalmente:

- `clientes`: dados cadastrais e status geral do cliente.
- `mensalidades`: parcelas, meses de referência, vencimentos, valores e
  pagamentos individuais.
- `configuracoes`: nome da empresa, chave PIX e banco/favorecido.

O arquivo é local e está incluído no `.gitignore`. Para fazer backup, copie o
`clientes.db` com a aplicação fechada.

## 🛠️ Solução de problemas

### A mensagem não é enviada

- Confirme que o WhatsApp Web está autenticado.
- Verifique se o navegador foi localizado ou se o navegador padrão está
  disponível.
- Não mova o foco para outra janela durante os 15 segundos de carregamento.
- Confira se o telefone possui DDD e está correto.
- Verifique o terminal para mensagens de erro da automação.

### Nenhuma cobrança foi gerada

- No disparo automático, confirme se há mensalidades com pelo menos 3 dias de
  atraso.
- Verifique a carência de 2 dias desde o último envio.
- No disparo manual pela interface, clientes em aberto podem ser enviados
  imediatamente.
- Confirme se o cliente não está marcado como `Pago`.

### O banco precisa ser reiniciado

Feche a aplicação e faça uma cópia de segurança de `clientes.db` antes de
qualquer manutenção. A exclusão do banco fará o sistema recriar uma estrutura
vazia na próxima execução.

## 📄 Licença

Este projeto é destinado a uso local e interno. Adicione uma licença formal ao
repositório caso ele seja distribuído publicamente.
