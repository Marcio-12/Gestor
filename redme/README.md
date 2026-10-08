# Gestor de clientes

Programa de terminal para cadastrar clientes, registrar pagamentos e verificar
status de pagamento usando Python, MySQL e `mysql-connector-python`.

## Menu

- Cadastrar novo cliente, incluindo telefone, valor e vencimento.
- Registrar o pagamento de um cliente.
- Listar clientes com status (`Pendente`, `Pago` ou `Atrasado`).
- Gerar cobrancas no 3o dia de atraso e depois a cada 2 dias, com link para WhatsApp.
- Sair do programa.

Ao gerar uma cobranca, o programa salva a data em `ultimo_envio_cobranca`.
Assim, a mesma cobranca nao e gerada novamente no mesmo dia e o proximo envio
respeita o intervalo de dois dias.

## Configuração da senha

A senha do MySQL não fica dentro do código e não deve ser enviada ao GitHub.
Ela fica no arquivo local `.env`, que está protegido pelo `.gitignore`.

1. Instale o Python e o MySQL.
2. Na pasta do projeto, instale as dependências:

   ```powershell
   pip install -r requirements.txt
   ```

3. Copie `.env.example` para um novo arquivo chamado `.env`:

   ```powershell
   Copy-Item .env.example .env
   ```

4. Abra `.env` e troque `coloque_sua_senha_aqui` pela senha do seu MySQL:

   ```text
   MYSQL_HOST=localhost
   MYSQL_USER=root
   MYSQL_PASSWORD=sua_senha
   MYSQL_DATABASE=clientes_db
   ```

5. Execute o programa:

   ```powershell
   python gestor.py
   ```

O banco `clientes_db` e a tabela `clientes` serão criados automaticamente.

## Importante

- Nunca substitua `MYSQL_PASSWORD` por uma senha diretamente em `gestor.py`.
- Nunca faça `git add .env`.
- O arquivo `.env.example` é apenas um modelo e não contém a senha real.
- Se a senha já foi publicada no GitHub, troque-a no MySQL imediatamente.

## Enviar para o GitHub

Depois de criar ou abrir o repositório local, confira se `.env` não aparece no
resultado de `git status` e execute:

```powershell
git add gestor.py requirements.txt .env.example .gitignore redme/README.md
git commit -m "Protege senha do banco e adiciona documentação"
git push
```
