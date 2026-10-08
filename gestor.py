"""Sistema de gestao e cobranca de clientes."""

import os
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import quote

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "clientes_db")


def conectar_banco():
	"""Cria ou atualiza a estrutura do banco e retorna uma conexao."""
	if not MYSQL_PASSWORD:
		raise RuntimeError(
			"MYSQL_PASSWORD nao foi configurada. "
			"Defina essa variavel no arquivo .env."
		)

	configuracao = {
		"host": MYSQL_HOST,
		"user": MYSQL_USER,
		"password": MYSQL_PASSWORD,
	}
	conexao_servidor = mysql.connector.connect(**configuracao)
	try:
		cursor = conexao_servidor.cursor()
		cursor.execute(
			f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}`"
		)
		cursor.close()
	finally:
		conexao_servidor.close()

	conexao = mysql.connector.connect(
		database=MYSQL_DATABASE,
		**configuracao,
	)
	try:
		cursor = conexao.cursor()
		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS clientes (
				id INT AUTO_INCREMENT PRIMARY KEY,
				nome VARCHAR(150) NOT NULL,
				telefone VARCHAR(30) NOT NULL,
				valor_mensalidade DECIMAL(10, 2) NOT NULL,
				data_vencimento DATE NOT NULL,
				status_pagamento VARCHAR(30) DEFAULT 'Pendente',
				ultimo_envio_cobranca DATE NULL
			)
			"""
		)
		cursor.close()
		_adicionar_colunas_antigas(conexao)
		conexao.commit()
	except Exception:
		conexao.close()
		raise
	return conexao


def _adicionar_colunas_antigas(conexao):
	"""Adiciona colunas novas quando o banco veio de uma versao anterior."""
	cursor = conexao.cursor()
	try:
		cursor.execute("SHOW COLUMNS FROM clientes LIKE 'data_vencimento'")
		if cursor.fetchone() is None:
			cursor.execute(
				"""
				ALTER TABLE clientes
				ADD COLUMN data_vencimento DATE NOT NULL
				"""
			)

		cursor.execute(
			"SHOW COLUMNS FROM clientes LIKE 'ultimo_envio_cobranca'"
		)
		if cursor.fetchone() is None:
			cursor.execute(
				"""
				ALTER TABLE clientes
				ADD COLUMN ultimo_envio_cobranca DATE NULL
				"""
			)
	finally:
		cursor.close()


def _ler_data_vencimento():
	"""Le uma data no formato brasileiro e converte para date."""
	try:
		return datetime.strptime(
			input("Data de vencimento (DD/MM/AAAA): ").strip(),
			"%d/%m/%Y",
		).date()
	except ValueError:
		print("Data invalida. Use o formato DD/MM/AAAA.")
		return None


def cadastrar_cliente(conexao):
	"""Cadastra um cliente com seus dados de cobranca."""
	nome = input("Nome completo: ").strip()
	telefone = input("Telefone: ").strip()
	data_vencimento = _ler_data_vencimento()

	try:
		valor = Decimal(input("Valor da mensalidade: ").strip().replace(",", "."))
	except InvalidOperation:
		print("Informe um valor numerico valido.")
		return

	if not nome or not telefone or valor <= 0 or data_vencimento is None:
		print("Nome, telefone, valor e data sao obrigatorios.")
		return

	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			INSERT INTO clientes
				(nome, telefone, valor_mensalidade, data_vencimento,
				 status_pagamento)
			VALUES (%s, %s, %s, %s, %s)
			""",
			(nome, telefone, valor, data_vencimento, "Pendente"),
		)
		conexao.commit()
		print("Cliente cadastrado com sucesso!")
	finally:
		cursor.close()


def listar_clientes(conexao):
	"""Exibe os clientes e atualiza status vencido quando necessario."""
	cursor = conexao.cursor(dictionary=True)
	try:
		cursor.execute(
			"""
			SELECT id, nome, telefone, valor_mensalidade, data_vencimento,
				   status_pagamento, ultimo_envio_cobranca
			FROM clientes
			ORDER BY nome
			"""
		)
		clientes = cursor.fetchall()
	finally:
		cursor.close()

	if not clientes:
		print("Nenhum cliente cadastrado.")
		return []

	hoje = date.today()
	for cliente in clientes:
		if (
			cliente["status_pagamento"] != "Pago"
			and cliente["data_vencimento"] < hoje
		):
			cliente["status_pagamento"] = "Atrasado"

	print("\n--- CLIENTES ---")
	for cliente in clientes:
		data_formatada = cliente["data_vencimento"].strftime("%d/%m/%Y")
		print(
			f"ID: {cliente['id']} | Nome: {cliente['nome']} | "
			f"Telefone: {cliente['telefone']} | "
			f"Valor: R$ {cliente['valor_mensalidade']:.2f} | "
			f"Vencimento: {data_formatada} | "
			f"Status: {cliente['status_pagamento']}"
		)
	return clientes


def registrar_pagamento(conexao):
	"""Marca o cliente escolhido como pago."""
	if not listar_clientes(conexao):
		return

	try:
		cliente_id = int(input("Digite o ID do cliente: "))
	except ValueError:
		print("Informe um ID numerico valido.")
		return

	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			UPDATE clientes
			SET status_pagamento = %s
			WHERE id = %s
			""",
			("Pago", cliente_id),
		)
		if cursor.rowcount == 0:
			print("Cliente nao encontrado.")
			return
		conexao.commit()
		print("Pagamento registrado com sucesso!")
	finally:
		cursor.close()


def _telefone_whatsapp(telefone):
	"""Retorna somente os digitos, incluindo o codigo do Brasil quando necessario."""
	digitos = re.sub(r"\D", "", telefone)
	if not digitos.startswith("55"):
		digitos = f"55{digitos}"
	return digitos


def gerar_cobrancas(conexao):
	"""Gera alertas nos dias 3, 5, 7... de atraso e registra o envio."""
	hoje = date.today()
	cursor = conexao.cursor(dictionary=True)
	try:
		cursor.execute(
			"""
			SELECT id, nome, telefone, valor_mensalidade, data_vencimento,
				   status_pagamento, ultimo_envio_cobranca
			FROM clientes
			WHERE status_pagamento <> %s
			ORDER BY nome
			""",
			("Pago",),
		)
		clientes = cursor.fetchall()
	finally:
		cursor.close()

	quantidade = 0
	for cliente in clientes:
		dias_atraso = (hoje - cliente["data_vencimento"]).days
		if dias_atraso < 3:
			continue

		ultimo_envio = cliente["ultimo_envio_cobranca"]
		deve_enviar = (
			(ultimo_envio is None and dias_atraso >= 3)
			or (
				ultimo_envio is not None
				and (hoje - ultimo_envio).days >= 2
			)
		)
		if not deve_enviar:
			continue

		valor = f"{cliente['valor_mensalidade']:.2f}".replace(".", ",")
		mensagem = (
			f"Olá, {cliente['nome']}! Identificamos uma mensalidade de "
			f"R$ {valor} em aberto há {dias_atraso} dias. "
			"Por favor, entre em contato para regularizar. Obrigado!"
		)
		link = (
			f"https://wa.me/{_telefone_whatsapp(cliente['telefone'])}"
			f"?text={quote(mensagem)}"
		)
		print(f"\nCobranca para {cliente['nome']}:")
		print(link)

		cursor = conexao.cursor()
		try:
			cursor.execute(
				"""
				UPDATE clientes
				SET ultimo_envio_cobranca = %s, status_pagamento = %s
				WHERE id = %s
				""",
				(hoje, "Atrasado", cliente["id"]),
			)
			conexao.commit()
		finally:
			cursor.close()
		quantidade += 1

	if quantidade == 0:
		print("Nenhuma cobranca deve ser gerada hoje.")


def excluir_cliente(conexao):
	"""Exclui do banco o cliente confirmado pelo usuario."""
	if not listar_clientes(conexao):
		return

	try:
		cliente_id = int(input("Digite o ID do cliente que deseja excluir: "))
	except ValueError:
		print("Informe um ID numerico valido.")
		return

	confirmacao = input(
		f"Tem certeza que deseja excluir o cliente ID {cliente_id}? (S/N): "
	).strip().upper()
	if confirmacao != "S":
		print("Exclusao cancelada.")
		return

	cursor = conexao.cursor()
	try:
		cursor.execute(
			"DELETE FROM clientes WHERE id = %s",
			(cliente_id,),
		)
		if cursor.rowcount == 0:
			print("Cliente não encontrado.")
			return
		conexao.commit()
		print("Cliente excluído com sucesso!")
	finally:
		cursor.close()


def menu():
	"""Executa o menu principal do sistema."""
	conexao = None
	try:
		conexao = conectar_banco()
		while True:
			print("\n--- MENU ---")
			print("1 - Cadastrar novo cliente")
			print("2 - Registrar pagamento (dar baixa)")
			print("3 - Listar todos os clientes e status")
			print("4 - Gerar alertas e cobrancas para WhatsApp")
			print("5 - Excluir cliente")
			print("0 - Sair do programa")

			opcao = input("Escolha uma opcao: ").strip()
			if opcao == "1":
				cadastrar_cliente(conexao)
			elif opcao == "2":
				registrar_pagamento(conexao)
			elif opcao == "3":
				listar_clientes(conexao)
			elif opcao == "4":
				gerar_cobrancas(conexao)
			elif opcao == "5":
				excluir_cliente(conexao)
			elif opcao == "0":
				print("Programa encerrado.")
				break
			else:
				print("Opcao invalida.")
	except Error as erro:
		print(f"Erro de banco de dados: {erro}")
	except RuntimeError as erro:
		print(f"Erro de configuracao: {erro}")
	finally:
		if conexao is not None and conexao.is_connected():
			conexao.close()


if __name__ == "__main__":
	menu()
