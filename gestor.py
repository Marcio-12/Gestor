"""Sistema de gestao e cobranca de clientes."""

import re
import random
import sqlite3
import calendar
import os
import subprocess
import time
import webbrowser
import pyautogui
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from math import isfinite
from urllib.parse import quote

CAMINHO_BANCO = "clientes.db"


def localizar_navegador_windows():
	"""Retorna o primeiro navegador instalado nos caminhos usuais."""
	diretorios = [
		os.environ.get("PROGRAMFILES"),
		os.environ.get("PROGRAMFILES(X86)"),
		os.environ.get("LOCALAPPDATA"),
	]
	executaveis = (
		("Google", "Chrome", "Application", "chrome.exe"),
		("Microsoft", "Edge", "Application", "msedge.exe"),
		("Mozilla Firefox", "firefox.exe"),
	)
	for partes in executaveis:
		for diretorio in diretorios:
			if not diretorio:
				continue
			caminho = os.path.join(diretorio, *partes)
			if os.path.isfile(caminho):
				return caminho
	return None


def abrir_link_whatsapp(url):
	"""Abre o WhatsApp Web, aguarda o carregamento e envia a mensagem."""
	try:
		navegador = localizar_navegador_windows()
		if navegador:
			try:
				subprocess.Popen(
					[navegador, url],
					stdin=subprocess.DEVNULL,
					stdout=subprocess.DEVNULL,
					stderr=subprocess.DEVNULL,
				)
			except OSError:
				navegador = None
		if not navegador and not webbrowser.open(url):
			return False

		time.sleep(15)
		pyautogui.press("enter")
		time.sleep(2)
		pyautogui.hotkey("ctrl", "w")
		return True
	except (
		OSError,
		RuntimeError,
		ValueError,
		webbrowser.Error,
		pyautogui.PyAutoGUIException,
	) as erro:
		print(f"Falha ao enviar cobranca pelo WhatsApp: {erro}")
		return False


def conectar_banco():
	"""Cria ou atualiza a estrutura do banco e retorna uma conexao."""
	conexao = sqlite3.connect(CAMINHO_BANCO)
	conexao.row_factory = sqlite3.Row
	try:
		cursor = conexao.cursor()
		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS clientes (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				nome TEXT NOT NULL,
				telefone TEXT NOT NULL,
				valor_mensalidade REAL NOT NULL,
				data_vencimento TEXT NOT NULL,
				status_pagamento TEXT DEFAULT 'Pendente',
				ultimo_envio_cobranca TEXT NULL
			)
			"""
		)
		cursor.close()
		_adicionar_colunas_antigas(conexao)
		_criar_tabela_configuracoes(conexao)
		_criar_tabela_mensalidades(conexao)
		_sincronizar_mensalidades_existentes(conexao)
		conexao.commit()
	except Exception:
		conexao.close()
		raise
	return conexao


def _criar_tabela_mensalidades(conexao):
	"""Cria a tabela de controle individual das mensalidades."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS mensalidades (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				cliente_id INTEGER NOT NULL,
				mes_referencia TEXT NOT NULL,
				valor REAL NOT NULL,
				data_vencimento TEXT NOT NULL,
				status TEXT NOT NULL DEFAULT 'Pendente'
					CHECK (status IN ('Pendente', 'Atrasado', 'Pago')),
				data_pagamento TEXT NULL,
				FOREIGN KEY (cliente_id) REFERENCES clientes(id),
				UNIQUE (cliente_id, mes_referencia)
			)
			"""
		)
	finally:
		cursor.close()


def _avancar_mes(ano, mes):
	mes += 1
	if mes == 13:
		return ano + 1, 1
	return ano, mes


def _sincronizar_mensalidades_cliente(
	conexao, cliente_id, data_vencimento, valor, status_inicial=None
):
	"""Gera registros mensais sem alterar pagamentos ja baixados."""
	hoje = date.today()
	if (data_vencimento.year, data_vencimento.month) > (
		hoje.year, hoje.month
	):
		return

	cursor = conexao.cursor()
	try:
		ano, mes = data_vencimento.year, data_vencimento.month
		while (ano, mes) <= (hoje.year, hoje.month):
			dia = min(
				data_vencimento.day,
				calendar.monthrange(ano, mes)[1],
			)
			vencimento = date(ano, mes, dia)
			status = "Atrasado" if vencimento < hoje else "Pendente"
			if status_inicial == "Pago":
				status = "Pago"
			cursor.execute(
				"""
				INSERT OR IGNORE INTO mensalidades
					(cliente_id, mes_referencia, valor, data_vencimento, status)
				VALUES (?, ?, ?, ?, ?)
				""",
				(
					cliente_id,
					f"{mes:02d}/{ano}",
					valor,
					vencimento.isoformat(),
					status,
				),
			)
			ano, mes = _avancar_mes(ano, mes)
	finally:
		cursor.close()


def _sincronizar_mensalidades_existentes(conexao):
	"""Migra clientes antigos para o controle mensal individual."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			SELECT id, valor_mensalidade, data_vencimento, status_pagamento
			FROM clientes
			"""
		)
		clientes = cursor.fetchall()
	finally:
		cursor.close()

	for cliente in clientes:
		_sincronizar_mensalidades_cliente(
			conexao,
			cliente["id"],
			date.fromisoformat(cliente["data_vencimento"]),
			cliente["valor_mensalidade"],
			cliente["status_pagamento"],
		)


def listar_mensalidades_abertas(conexao, cliente_id):
	"""Retorna mensalidades pendentes ou atrasadas de um cliente."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			SELECT id, cliente_id, mes_referencia, valor, data_vencimento,
				   status, data_pagamento
			FROM mensalidades
			WHERE cliente_id = ? AND status IN (?, ?)
			ORDER BY data_vencimento, id
			""",
			(cliente_id, "Pendente", "Atrasado"),
		)
		return [dict(linha) for linha in cursor.fetchall()]
	finally:
		cursor.close()


def dar_baixa_mensalidades(conexao, lista_ids_mensalidades):
	"""Baixa somente as mensalidades selecionadas e atualiza o cliente."""
	ids = list(dict.fromkeys(lista_ids_mensalidades))
	if not ids:
		raise ValueError("Selecione ao menos uma mensalidade.")

	cursor = conexao.cursor()
	try:
		placeholders = ",".join("?" for _ in ids)
		cursor.execute(
			f"""
			SELECT DISTINCT cliente_id
			FROM mensalidades
			WHERE id IN ({placeholders})
			  AND status IN (?, ?)
			""",
			(*ids, "Pendente", "Atrasado"),
		)
		cliente_ids = [linha["cliente_id"] for linha in cursor.fetchall()]
		if not cliente_ids:
			raise ValueError("Nenhuma mensalidade aberta foi encontrada.")

		cursor.execute(
			f"""
			UPDATE mensalidades
			SET status = ?, data_pagamento = ?
			WHERE id IN ({placeholders})
			  AND status IN (?, ?)
			""",
			("Pago", date.today().isoformat(), *ids, "Pendente", "Atrasado"),
		)
		quantidade_baixada = cursor.rowcount

		for cliente_id in cliente_ids:
			cursor.execute(
				"""
				UPDATE clientes
				SET status_pagamento = CASE
					WHEN EXISTS (
						SELECT 1 FROM mensalidades
						WHERE cliente_id = clientes.id
						  AND status IN ('Pendente', 'Atrasado')
					) THEN CASE
						WHEN EXISTS (
							SELECT 1 FROM mensalidades
							WHERE cliente_id = clientes.id
							  AND status = 'Atrasado'
						) THEN 'Atrasado'
						ELSE 'Pendente'
					END
					ELSE 'Pago'
				END
				WHERE id = ?
				""",
				(cliente_id,),
			)
		conexao.commit()
		return quantidade_baixada
	except (sqlite3.Error, ValueError):
		conexao.rollback()
		raise
	finally:
		cursor.close()


def _criar_tabela_configuracoes(conexao):
	"""Cria e migra a configuracao unica usada nas cobrancas."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS configuracoes (
				id INTEGER PRIMARY KEY CHECK (id = 1),
				nome_empresa TEXT NOT NULL DEFAULT '',
				chave_pix TEXT NOT NULL DEFAULT '',
				nome_banco TEXT NOT NULL DEFAULT ''
			)
			"""
		)
		cursor.execute("PRAGMA table_info(configuracoes)")
		colunas = {linha["name"] for linha in cursor.fetchall()}
		if "nome_banco" not in colunas:
			cursor.execute(
				"ALTER TABLE configuracoes ADD COLUMN nome_banco TEXT "
				"NOT NULL DEFAULT ''"
			)
		cursor.execute(
			"""
			INSERT OR IGNORE INTO configuracoes
				(id, nome_empresa, chave_pix, nome_banco)
			VALUES (1, '', '', '')
			"""
		)
	finally:
		cursor.close()


def salvar_configuracoes(conexao, nome_empresa, chave_pix, nome_banco):
	"""Persiste os dados usados nas mensagens de cobranca."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			INSERT INTO configuracoes (id, nome_empresa, chave_pix, nome_banco)
			VALUES (1, ?, ?, ?)
			ON CONFLICT(id) DO UPDATE SET
				nome_empresa = excluded.nome_empresa,
				chave_pix = excluded.chave_pix,
				nome_banco = excluded.nome_banco
			""",
			(
				str(nome_empresa or "").strip(),
				str(chave_pix or "").strip(),
				str(nome_banco or "").strip(),
			),
		)
		conexao.commit()
		return True
	except sqlite3.Error:
		conexao.rollback()
		raise
	finally:
		cursor.close()


def limpar_configuracoes(conexao):
	"""Remove os dados da empresa usados nas mensagens de cobranca."""
	cursor = conexao.cursor()
	try:
		cursor.execute("DELETE FROM configuracoes")
		conexao.commit()
		return True
	except sqlite3.Error:
		conexao.rollback()
		raise
	finally:
		cursor.close()


def obter_configuracoes(conexao):
	"""Retorna nome da empresa, chave PIX e banco/favorecido."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			SELECT nome_empresa, chave_pix, nome_banco
			FROM configuracoes
			WHERE id = ?
			""",
			(1,),
		)
		linha = cursor.fetchone()
		if linha is None:
			return {"nome_empresa": "", "chave_pix": "", "nome_banco": ""}
		return dict(linha)
	finally:
		cursor.close()


def _adicionar_colunas_antigas(conexao):
	"""Adiciona colunas novas quando o banco veio de uma versao anterior."""
	cursor = conexao.cursor()
	try:
		cursor.execute("PRAGMA table_info(clientes)")
		colunas = {linha["name"] for linha in cursor.fetchall()}
		if "data_vencimento" not in colunas:
			cursor.execute(
				"""
				ALTER TABLE clientes
				ADD COLUMN data_vencimento TEXT
				"""
			)

		if "ultimo_envio_cobranca" not in colunas:
			cursor.execute(
				"""
				ALTER TABLE clientes
				ADD COLUMN ultimo_envio_cobranca TEXT NULL
				"""
			)
	finally:
		cursor.close()


def _data_vencimento_do_dia(dia, hoje=None):
	"""Converte um dia do mes na data valida mais proxima deste mes."""
	if not isinstance(dia, int) or isinstance(dia, bool) or not 1 <= dia <= 31:
		raise ValueError("O dia do vencimento deve ser um inteiro entre 1 e 31.")
	hoje = hoje or date.today()
	dia = min(dia, calendar.monthrange(hoje.year, hoje.month)[1])
	return date(hoje.year, hoje.month, dia)


def _ler_data_vencimento():
	"""Le apenas o dia do vencimento e ajusta dias inexistentes do mes."""
	valor = input("Dia de vencimento (1 a 31): ").strip()
	if not re.fullmatch(r"[0-9]+", valor):
		print("Informe apenas um numero inteiro entre 1 e 31.")
		return None
	try:
		return _data_vencimento_do_dia(int(valor))
	except ValueError as erro:
		print(erro)
		return None


def _normalizar_nome(nome):
	nome = str(nome or "").strip()
	if not nome:
		raise ValueError("Informe o nome completo do cliente.")
	return nome.title()


def _normalizar_telefone(telefone):
	digitos = re.sub(r"\D", "", str(telefone or ""))
	if digitos.startswith("55") and len(digitos) in (12, 13):
		numero = digitos[2:]
	else:
		numero = digitos
	if len(numero) not in (10, 11):
		raise ValueError("Informe um telefone com DDD (10 ou 11 digitos).")
	return f"55{numero}"


def _normalizar_valor(valor):
	texto = str(valor or "").strip().replace(",", ".")
	if not re.fullmatch(r"\d+(?:\.\d{1,2})?", texto):
		raise ValueError("Informe um valor numerico positivo, como 150,00.")
	try:
		resultado = float(Decimal(texto))
	except (InvalidOperation, ValueError):
		raise ValueError("Informe um valor numerico positivo, como 150,00.")
	if not isfinite(resultado) or resultado <= 0:
		raise ValueError("O valor da mensalidade deve ser maior que zero.")
	return resultado


def _normalizar_data_vencimento(valor):
	if isinstance(valor, date):
		return valor
	texto = str(valor or "").strip()
	if re.fullmatch(r"[0-9]+", texto):
		return _data_vencimento_do_dia(int(texto))
	try:
		return datetime.strptime(texto, "%d/%m/%Y").date()
	except ValueError:
		raise ValueError("Informe apenas o dia do vencimento, entre 1 e 31.")


def _ler_datas_atrasadas(valor):
	"""Converte a lista opcional de datas historicas em datas unicas."""
	texto = str(valor or "").strip()
	if not texto:
		return []
	datas = []
	for item in texto.split(","):
		item = item.strip()
		try:
			data = datetime.strptime(item, "%d/%m/%Y").date()
		except ValueError:
			raise ValueError(
				"Use as datas atrasadas no formato DD/MM/AAAA, separadas por virgula."
			)
		if data not in datas:
			datas.append(data)
	return datas


def cadastrar_cliente(
	conexao,
	nome=None,
	telefone=None,
	valor=None,
	dia_vencimento=None,
	datas_atrasadas=None,
):
	"""Cadastra um cliente com seus dados de cobranca."""
	modo_terminal = nome is None
	if modo_terminal:
		nome = input("Nome completo: ")
		telefone = input("Telefone: ")
		valor = input("Valor da mensalidade: ")
		data_vencimento = _ler_data_vencimento()
		datas_atrasadas = input(
			"Datas atrasadas (opcional, DD/MM/AAAA separadas por virgula): "
		)
		if data_vencimento is None:
			return False
	else:
		data_vencimento = _normalizar_data_vencimento(dia_vencimento)

	try:
		nome = _normalizar_nome(nome)
		telefone = _normalizar_telefone(telefone)
		valor = _normalizar_valor(valor)
		datas_atrasadas = _ler_datas_atrasadas(datas_atrasadas)
		if modo_terminal:
			data_vencimento = _normalizar_data_vencimento(data_vencimento)
	except ValueError as erro:
		if modo_terminal:
			print(erro)
			return False
		raise

	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			INSERT INTO clientes
				(nome, telefone, valor_mensalidade, data_vencimento,
				 status_pagamento)
			VALUES (?, ?, ?, ?, ?)
			""",
			(
				nome,
				telefone,
				valor,
				data_vencimento.isoformat(),
				"Atrasado" if datas_atrasadas else "Pendente",
			),
		)
		cliente_id = cursor.lastrowid
		if datas_atrasadas:
			for data_atrasada in datas_atrasadas:
				cursor.execute(
					"""
					INSERT INTO mensalidades
						(cliente_id, mes_referencia, valor, data_vencimento, status)
					VALUES (?, ?, ?, ?, ?)
					""",
					(
						cliente_id,
						data_atrasada.strftime("%m/%Y"),
						valor,
						data_atrasada.isoformat(),
						"Atrasado",
					),
				)
		else:
			data_atual = date.today()
			dia = min(
				data_vencimento.day,
				calendar.monthrange(data_atual.year, data_atual.month)[1],
			)
			data_mensalidade = date(data_atual.year, data_atual.month, dia)
			cursor.execute(
				"""
				INSERT INTO mensalidades
					(cliente_id, mes_referencia, valor, data_vencimento, status)
				VALUES (?, ?, ?, ?, ?)
				""",
				(
					cliente_id,
					data_atual.strftime("%m/%Y"),
					valor,
					data_mensalidade.isoformat(),
					"Atrasado" if data_mensalidade < date.today() else "Pendente",
				),
			)
		conexao.commit()
		print("Cliente cadastrado com sucesso!")
	finally:
		cursor.close()
	return True


def atualizar_cliente(
	conexao,
	cliente_id,
	nome,
	telefone,
	valor_mensalidade,
	dia_vencimento,
	datas_atrasadas=None,
):
	"""Atualiza os dados cadastrais de um cliente existente."""
	nome = _normalizar_nome(nome)
	telefone = _normalizar_telefone(telefone)
	valor_mensalidade = _normalizar_valor(valor_mensalidade)
	data_vencimento = _normalizar_data_vencimento(dia_vencimento)
	datas_atrasadas = _ler_datas_atrasadas(datas_atrasadas)

	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			UPDATE clientes
			SET nome = ?, telefone = ?, valor_mensalidade = ?,
			    data_vencimento = ?
			WHERE id = ?
			""",
			(
				nome,
				telefone,
				valor_mensalidade,
				data_vencimento.isoformat(),
				cliente_id,
			),
		)
		if cursor.rowcount == 0:
			raise ValueError("Cliente nao encontrado.")
		cursor.execute(
			"""
			DELETE FROM mensalidades
			WHERE cliente_id = ? AND status IN (?, ?)
			""",
			(cliente_id, "Pendente", "Atrasado"),
		)
		if datas_atrasadas:
			for data_atrasada in datas_atrasadas:
				cursor.execute(
					"""
					INSERT INTO mensalidades
						(cliente_id, mes_referencia, valor, data_vencimento, status)
					VALUES (?, ?, ?, ?, ?)
					""",
					(
						cliente_id,
						data_atrasada.strftime("%m/%Y"),
						valor_mensalidade,
						data_atrasada.isoformat(),
						"Atrasado",
					),
				)
			status_cliente = "Atrasado"
		else:
			data_atual = date.today()
			dia = min(
				data_vencimento.day,
				calendar.monthrange(data_atual.year, data_atual.month)[1],
			)
			data_mensalidade = date(data_atual.year, data_atual.month, dia)
			cursor.execute(
				"""
				INSERT INTO mensalidades
					(cliente_id, mes_referencia, valor, data_vencimento, status)
				VALUES (?, ?, ?, ?, ?)
				""",
				(
					cliente_id,
					data_atual.strftime("%m/%Y"),
					valor_mensalidade,
					data_mensalidade.isoformat(),
					"Atrasado" if data_mensalidade < date.today() else "Pendente",
				),
			)
			status_cliente = (
				"Atrasado"
				if data_mensalidade < date.today()
				else "Pendente"
			)
		cursor.execute(
			"UPDATE clientes SET status_pagamento = ? WHERE id = ?",
			(status_cliente, cliente_id),
		)
		conexao.commit()
		return True
	except sqlite3.Error:
		conexao.rollback()
		raise
	finally:
		cursor.close()


def listar_clientes(conexao):
	"""Exibe os clientes e atualiza status vencido quando necessario."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			SELECT id, nome, telefone, valor_mensalidade, data_vencimento,
				   status_pagamento, ultimo_envio_cobranca
			FROM clientes
			ORDER BY nome
			"""
		)
		clientes = [dict(linha) for linha in cursor.fetchall()]
	finally:
		cursor.close()

	if not clientes:
		print("Nenhum cliente cadastrado.")
		return []

	hoje = date.today()
	for cliente in clientes:
		cliente["data_vencimento"] = date.fromisoformat(
			cliente["data_vencimento"]
		)
		if cliente["ultimo_envio_cobranca"] is not None:
			cliente["ultimo_envio_cobranca"] = date.fromisoformat(
				cliente["ultimo_envio_cobranca"]
			)
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


def registrar_pagamento(conexao, cliente_id):
	"""Mantem compatibilidade e baixa todas as mensalidades abertas."""
	mensalidades = listar_mensalidades_abertas(conexao, cliente_id)
	if mensalidades:
		return dar_baixa_mensalidades(
			conexao, [mensalidade["id"] for mensalidade in mensalidades]
		)

	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			UPDATE clientes
			SET status_pagamento = ?
			WHERE id = ?
			""",
			("Pago", cliente_id),
		)
		if cursor.rowcount == 0:
			raise ValueError("Cliente nao encontrado.")
		conexao.commit()
		return True
	except sqlite3.Error:
		conexao.rollback()
		raise
	finally:
		cursor.close()


def _telefone_whatsapp(telefone):
	"""Retorna somente os digitos, incluindo o codigo do Brasil quando necessario."""
	return _normalizar_telefone(telefone)


def _meses_pendentes(data_vencimento, hoje):
	"""Lista os meses em aberto desde o vencimento registrado ate hoje."""
	if (hoje.year, hoje.month) < (
		data_vencimento.year,
		data_vencimento.month,
	):
		return []

	meses = (
		"Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
		"Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
	)
	ano, mes = data_vencimento.year, data_vencimento.month
	pendentes = []
	while (ano, mes) <= (hoje.year, hoje.month):
		pendentes.append(f"{meses[mes - 1]}/{ano}")
		mes += 1
		if mes == 13:
			mes = 1
			ano += 1
	return pendentes


def gerar_cobrancas(conexao, forcar=False):
	"""Gera cobrancas automaticas ou manuais e registra os envios.

	Quando ``forcar`` e falso, aplica a regra de tres dias de atraso e
	carencia de dois dias. O modo forcado e destinado ao disparo manual
	da empresa e ignora apenas essas restricoes de calendario.
	"""
	hoje = date.today()
	configuracoes = obter_configuracoes(conexao)
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			SELECT id, nome, telefone, valor_mensalidade, data_vencimento,
				   status_pagamento, ultimo_envio_cobranca
			FROM clientes
			WHERE status_pagamento <> ?
			ORDER BY nome
			""",
			("Pago",),
		)
		clientes = [dict(linha) for linha in cursor.fetchall()]
	finally:
		cursor.close()

	quantidade = 0
	for cliente in clientes:
		mensalidades_abertas = listar_mensalidades_abertas(
			conexao, cliente["id"]
		)
		if not mensalidades_abertas:
			continue
		for mensalidade in mensalidades_abertas:
			data_mensalidade = date.fromisoformat(
				mensalidade["data_vencimento"]
			)
			if (
				data_mensalidade < hoje
				and mensalidade["status"] == "Pendente"
			):
				cursor = conexao.cursor()
				try:
					cursor.execute(
						"""
						UPDATE mensalidades
						SET status = ?
						WHERE id = ? AND status = ?
						""",
						("Atrasado", mensalidade["id"], "Pendente"),
					)
					conexao.commit()
					mensalidade["status"] = "Atrasado"
				finally:
					cursor.close()

		dias_atraso = max(
			(
				hoje - date.fromisoformat(m["data_vencimento"])
			).days
			for m in mensalidades_abertas
			if date.fromisoformat(m["data_vencimento"]) <= hoje
		) if any(
			date.fromisoformat(m["data_vencimento"]) <= hoje
			for m in mensalidades_abertas
		) else -1
		if not forcar:
			if dias_atraso < 3:
				continue

		ultimo_envio = cliente["ultimo_envio_cobranca"]
		if ultimo_envio is not None:
			ultimo_envio = date.fromisoformat(ultimo_envio)
		deve_enviar = (
			forcar
			or ultimo_envio is None
			or (hoje - ultimo_envio).days >= 2
		)
		if not deve_enviar:
			continue

		if forcar:
			mensalidades_cobranca = mensalidades_abertas
		else:
			mensalidades_cobranca = [
				m for m in mensalidades_abertas
				if date.fromisoformat(m["data_vencimento"]) <= hoje
			]
		meses_pendentes = [
			mensalidade["mes_referencia"]
			for mensalidade in mensalidades_cobranca
		]
		if forcar and not meses_pendentes:
			meses = (
				"Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
				"Julho", "Agosto", "Setembro", "Outubro", "Novembro",
				"Dezembro",
			)
			meses_pendentes = [f"{meses[hoje.month - 1]}/{hoje.year}"]
		if not meses_pendentes:
			continue
		if quantidade > 0:
			tempo_espera = random.randint(25, 45)
			print(
				f"Aguardando {tempo_espera} segundos antes da proxima "
				"cobranca..."
			)
			time.sleep(tempo_espera)
		quantidade_meses = len(meses_pendentes)
		valor_total = sum(
			mensalidade["valor"]
			for mensalidade in mensalidades_cobranca
		)
		resumo = (
			f"Constatamos em nosso sistema mensalidade(s) em aberto "
			f"referentes a ({', '.join(meses_pendentes)}), no valor total "
			f"de R$ {valor_total:.2f}."
		)
		mensagem = (
			f"Olá, {cliente['nome']}! Tudo bem?\n\n"
			f"Aqui é da {configuracoes['nome_empresa']}.\n\n"
			f"{resumo}\n\n"
			"Para sua comodidade, você pode efetuar o pagamento via PIX:\n"
			f"🔑 Chave PIX: {configuracoes['chave_pix']}\n"
			f"🏦 Banco/Favorecido: {configuracoes['nome_banco']}\n\n"
			"Caso já tenha efetuado o pagamento, por favor desconsidere esta "
			"mensagem.\n\n"
			"Qualquer dúvida estamos à disposição!"
		)
		mensagem_codificada = quote(mensagem)
		telefone = _telefone_whatsapp(cliente["telefone"])
		url = (
			f"https://web.whatsapp.com/send?phone="
			f"{telefone}&text={mensagem_codificada}"
		)
		print(f"\nCobranca para {cliente['nome']}:")
		print(url)
		if not abrir_link_whatsapp(url):
			continue

		cursor = conexao.cursor()
		try:
			cursor.execute(
				"""
				UPDATE clientes
				SET ultimo_envio_cobranca = ?, status_pagamento = ?
				WHERE id = ?
				""",
				(
					hoje.isoformat(),
					"Atrasado" if dias_atraso >= 1 else "Pendente",
					cliente["id"],
				),
			)
			conexao.commit()
		finally:
			cursor.close()
		quantidade += 1

	if quantidade == 0:
		print("Nenhuma cobranca foi gerada.")
	return quantidade


def excluir_cliente(conexao, cliente_id):
	"""Exclui o cliente e todo o historico de mensalidades associado."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"DELETE FROM mensalidades WHERE cliente_id = ?",
			(cliente_id,),
		)
		cursor.execute(
			"DELETE FROM clientes WHERE id = ?",
			(cliente_id,),
		)
		if cursor.rowcount == 0:
			raise ValueError("Cliente nao encontrado.")
		conexao.commit()
		return True
	except sqlite3.Error:
		conexao.rollback()
		raise
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
				try:
					cliente_id = int(input("Digite o ID do cliente: "))
					registrar_pagamento(conexao, cliente_id)
					print("Pagamento registrado com sucesso!")
				except ValueError as erro:
					print(erro)
			elif opcao == "3":
				listar_clientes(conexao)
			elif opcao == "4":
				gerar_cobrancas(conexao)
			elif opcao == "5":
				listar_clientes(conexao)
				try:
					cliente_id = int(input("Digite o ID do cliente: "))
					excluir_cliente(conexao, cliente_id)
					print("Cliente excluido com sucesso!")
				except (ValueError, sqlite3.Error) as erro:
					print(erro)
			elif opcao == "0":
				print("Programa encerrado.")
				break
			else:
				print("Opcao invalida.")
	except sqlite3.Error as erro:
		print(f"Erro de banco de dados: {erro}")
	finally:
		if conexao is not None:
			conexao.close()


if __name__ == "__main__":
	menu()
