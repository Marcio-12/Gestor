# Gestor de clientes

Programa de terminal para cadastrar clientes, registrar pagamentos e verificar
status de pagamento usando Python e SQLite.

## Menu

- Cadastrar novo cliente, incluindo telefone, valor e vencimento.
- Registrar o pagamento de um cliente.
- Listar clientes com status (`Pendente`, `Pago` ou `Atrasado`).
- Gerar cobrancas no 3o dia de atraso e depois a cada 2 dias, com link para WhatsApp.
- Sair do programa.

Ao gerar uma cobranca, o programa salva a data em `ultimo_envio_cobranca`.
Assim, a mesma cobranca nao e gerada novamente no mesmo dia e o proximo envio
respeita o intervalo de dois dias.

## Execução local

O programa usa o SQLite incluído no Python. Não é necessário instalar ou
configurar um servidor de banco de dados.

1. Instale o Python.
2. Na pasta do projeto, instale as dependências (o arquivo está vazio porque o
   programa usa apenas a biblioteca padrão):

   ```powershell
   pip install -r requirements.txt
   ```

3. Execute o programa:

   ```powershell
   python gestor.py
   ```

O arquivo local `clientes.db` e a tabela `clientes` serão criados
automaticamente na pasta do programa.

## Enviar para o GitHub

Depois de criar ou abrir o repositório local, execute:

```powershell
git add gestor.py requirements.txt redme/README.md
git commit -m "Migra banco de dados para SQLite"
git push
```
