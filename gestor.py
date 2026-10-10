"""Sistema de gestao e cobranca de clientes.

Copyright (c) 2026 Marcio Ramos. Todos os direitos reservados.
Este software e de autoria de Marcio Ramos.
"""

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
STATUS_ABERTOS = ("Pendente", "Atrasada")
STATUS_OFICIAIS = ("Pendente", "Atrasada", "Paga", "Em Acordo")
STATUS_FILTROS = ("Todas", *STATUS_OFICIAIS)
STATUS_PARCELA = ("Pendente", "Atrasada", "Em Acordo", "Adiantada", "Pago")


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
		_criar_metadata_sistema(conexao)
		_migrar_status_mensalidades(conexao)
		_sincronizar_mensalidades_existentes(conexao)
		_atualizar_status_vencidos(conexao)
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
					CHECK (status IN ('Pendente', 'Atrasada', 'Em Acordo',
						'Adiantada', 'Pago')),
				data_pagamento TEXT NULL,
				data_acordo TEXT NULL,
				valor_acordo REAL NULL,
				desconto_adiantado REAL NOT NULL DEFAULT 0,
				valor_pago REAL NULL,
				FOREIGN KEY (cliente_id) REFERENCES clientes(id),
				UNIQUE (cliente_id, mes_referencia)
			)
			"""
		)
	finally:
		cursor.close()


def _criar_metadata_sistema(conexao):
	"""Registra autoria e versao em uma tabela interna de metadados."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			CREATE TABLE IF NOT EXISTS sistema_metadata (
				chave TEXT PRIMARY KEY,
				valor TEXT NOT NULL
			)
			"""
		)
		cursor.executemany(
			"""
			INSERT INTO sistema_metadata (chave, valor)
			VALUES (?, ?)
			ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
			""",
			(
				("copyright", "Copyright (c) 2026 Marcio Ramos"),
				("autor", "Marcio Ramos"),
				("versao", "1.0.0"),
			),
		)
	finally:
		cursor.close()


def _migrar_status_mensalidades(conexao):
	"""Migra a tabela antiga, que aceitava apenas Atrasado, com seguranca."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"SELECT sql FROM sqlite_master WHERE type = 'table' "
			"AND name = 'mensalidades'"
		)
		sql_tabela = (cursor.fetchone() or {"sql": ""})["sql"] or ""
		if "Em Acordo" not in sql_tabela:
			cursor.execute("ALTER TABLE mensalidades RENAME TO mensalidades_legacy")
			_criar_tabela_mensalidades(conexao)
			cursor.execute(
				"""
				INSERT INTO mensalidades
					(id, cliente_id, mes_referencia, valor, data_vencimento,
					 status, data_pagamento)
				SELECT id, cliente_id, mes_referencia, valor, data_vencimento,
					CASE WHEN status = 'Atrasado' THEN 'Atrasada'
						 ELSE status END,
					data_pagamento
				FROM mensalidades_legacy
				"""
			)
			cursor.execute("DROP TABLE mensalidades_legacy")
		else:
			cursor.execute("PRAGMA table_info(mensalidades)")
			colunas = {linha["name"] for linha in cursor.fetchall()}
			for nome, tipo, padrao in (
				("data_acordo", "TEXT", "NULL"),
				("valor_acordo", "REAL", "NULL"),
				("desconto_adiantado", "REAL", "0"),
				("valor_pago", "REAL", "NULL"),
			):
				if nome not in colunas:
					cursor.execute(
						f"ALTER TABLE mensalidades ADD COLUMN {nome} {tipo} "
						f"DEFAULT {padrao}"
					)
		cursor.execute(
			"UPDATE mensalidades SET status = 'Atrasada' "
			"WHERE status = 'Atrasado'"
		)
	finally:
		cursor.close()


def _atualizar_status_vencidos(conexao):
	"""Marca como Atrasada somente a parcela aberta que venceu."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			UPDATE mensalidades
			SET status = 'Atrasada'
			WHERE status = 'Pendente' AND data_vencimento < ?
			""",
			(date.today().isoformat(),),
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
			status = "Atrasada" if vencimento < hoje else "Pendente"
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
			(cliente_id, *STATUS_ABERTOS),
		)
		return [dict(linha) for linha in cursor.fetchall()]
	finally:
		cursor.close()


def listar_clientes_filtro(conexao):
	"""Retorna clientes ordenados para o seletor da aba de parcelas."""
	cursor = conexao.cursor()
	try:
		cursor.execute("SELECT id, nome FROM clientes ORDER BY nome, id")
		return [dict(linha) for linha in cursor.fetchall()]
	finally:
		cursor.close()


def inserir_parcela(
	conexao, cliente_id, mes_referencia, valor, data_vencimento
):
	"""Insere uma nova parcela sem alterar o historico do cliente."""
	mes_referencia = str(mes_referencia or "").strip()
	if not re.fullmatch(r"\d{1,2}/\d{4}", mes_referencia):
		raise ValueError("Use a referencia da parcela no formato MM/AAAA.")
	valor = _normalizar_valor(valor)
	data_vencimento = _normalizar_data_vencimento(data_vencimento)
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			INSERT INTO mensalidades
				(cliente_id, mes_referencia, valor, data_vencimento, status)
			VALUES (?, ?, ?, ?, ?)
			""",
			(
				cliente_id,
				mes_referencia,
				valor,
				data_vencimento.isoformat(),
				(
					"Atrasada"
					if data_vencimento < date.today()
					else "Pendente"
				),
			),
		)
		conexao.commit()
		return cursor.lastrowid
	except sqlite3.IntegrityError as erro:
		conexao.rollback()
		raise ValueError(
			"Ja existe uma parcela com essa referencia para este cliente."
	) from erro
	except sqlite3.Error:
		conexao.rollback()
		raise
	finally:
		cursor.close()


def listar_parcelas(conexao, filtro="Atrasada", cliente_id=None):
	"""Lista parcelas por status e, opcionalmente, por cliente."""
	if filtro not in STATUS_FILTROS:
		raise ValueError("Filtro de parcelas invalido.")
	_atualizar_status_vencidos(conexao)
	statuses = {
		"Todas": STATUS_PARCELA,
		"Pendente": ("Pendente",),
		"Atrasada": ("Atrasada",),
		"Paga": ("Pago", "Adiantada"),
		"Em Acordo": ("Em Acordo",),
	}[filtro]
	placeholders = ",".join("?" for _ in statuses)
	cursor = conexao.cursor()
	try:
		cursor.execute(
			f"""
			SELECT m.id, m.cliente_id, c.nome AS cliente_nome,
				   m.mes_referencia, m.valor, m.data_vencimento,
				   m.status, m.data_pagamento, m.valor_acordo,
				   m.desconto_adiantado
			FROM mensalidades m
			JOIN clientes c ON c.id = m.cliente_id
			WHERE m.status IN ({placeholders})
			  AND (? IS NULL OR m.cliente_id = ?)
			ORDER BY m.data_vencimento, c.nome, m.id
			""",
			(*statuses, cliente_id, cliente_id),
		)
		return [dict(linha) for linha in cursor.fetchall()]
	finally:
		cursor.close()


def atualizar_status_mensalidade(conexao, mensalidade_id, novo_status):
	"""Atualiza imediatamente o status de uma parcela individual."""
	if novo_status == "Paga":
		novo_status = "Pago"
	if novo_status not in STATUS_PARCELA:
		raise ValueError("Status de parcela invalido.")
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"SELECT cliente_id FROM mensalidades WHERE id = ?",
			(mensalidade_id,),
		)
		linha = cursor.fetchone()
		if linha is None:
			raise ValueError("Parcela nao encontrada.")
		data_pagamento = (
			date.today().isoformat()
			if novo_status in ("Pago", "Adiantada")
			else None
		)
		cursor.execute(
			"""
			UPDATE mensalidades
			SET status = ?, data_pagamento = ?
			WHERE id = ?
			""",
			(novo_status, data_pagamento, mensalidade_id),
		)
		cliente_id = linha["cliente_id"]
		cursor.execute(
			"""
			UPDATE clientes
			SET status_pagamento = CASE
				WHEN EXISTS (
					SELECT 1 FROM mensalidades
					WHERE cliente_id = ? AND status = 'Atrasada'
				) THEN 'Atrasada'
				WHEN EXISTS (
					SELECT 1 FROM mensalidades
					WHERE cliente_id = ? AND status = 'Em Acordo'
				) THEN 'Em Acordo'
				WHEN EXISTS (
					SELECT 1 FROM mensalidades
					WHERE cliente_id = ?
					  AND status IN ('Pendente', 'Atrasada')
				) THEN 'Pendente'
				ELSE 'Pago'
			END
			WHERE id = ?
			""",
			(cliente_id, cliente_id, cliente_id, cliente_id),
		)
		conexao.commit()
	except (sqlite3.Error, ValueError):
		conexao.rollback()
		raise
	finally:
		cursor.close()


def dar_baixa_mensalidades(
	conexao, lista_ids_mensalidades, desconto_adiantado=0
):
	"""Baixa parcelas e registra Adiantada e desconto quando aplicavel."""
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
			(*ids, *STATUS_ABERTOS),
		)
		cliente_ids = [linha["cliente_id"] for linha in cursor.fetchall()]
		if not cliente_ids:
			raise ValueError("Nenhuma mensalidade aberta foi encontrada.")

		cursor.execute(
			f"""
			UPDATE mensalidades
			SET status = CASE WHEN data_vencimento > ? THEN 'Adiantada'
				ELSE 'Pago' END,
				data_pagamento = ?, desconto_adiantado = ?,
				valor_pago = MAX(0, valor - ?)
			WHERE id IN ({placeholders})
			  AND status IN (?, ?)
			""",
			(
				date.today().isoformat(),
				date.today().isoformat(),
				_normalizar_desconto(desconto_adiantado),
				_normalizar_desconto(desconto_adiantado),
				*ids,
				*STATUS_ABERTOS,
			),
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
						  AND status IN ('Pendente', 'Atrasada')
					) THEN CASE
						WHEN EXISTS (
							SELECT 1 FROM mensalidades
							WHERE cliente_id = clientes.id
							  AND status = 'Atrasada'
						) THEN 'Atrasada'
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


def _normalizar_desconto(valor):
	"""Valida desconto sem permitir valor negativo ou maior que a parcela."""
	try:
		desconto = float(Decimal(str(valor or 0).replace(",", ".")))
	except (InvalidOperation, ValueError):
		raise ValueError("Informe um desconto numerico valido.")
	if not isfinite(desconto) or desconto < 0:
		raise ValueError("O desconto nao pode ser negativo.")
	return desconto


def _normalizar_dias_regua(valor, tipo):
	"""Converte configuracoes da regua em inteiros positivos."""
	try:
		dias = int(str(valor).strip())
	except (TypeError, ValueError):
		raise ValueError(f"Informe um numero de dias valido para a regua {tipo}.")
	invalido = dias < 0 if tipo == "pre" else dias < 1
	if invalido:
		raise ValueError(
			"Os dias pre-vencimento nao podem ser negativos e o intervalo "
			"pos-vencimento deve ser maior que zero."
		)
	return dias


def registrar_acordo(conexao, mensalidade_id, nova_data, novo_valor):
	"""Renegocia uma parcela e congela cobrancas do vencimento original."""
	data_acordo = _normalizar_data_vencimento(nova_data)
	valor_acordo = _normalizar_valor(novo_valor)
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			UPDATE mensalidades
			SET status = 'Em Acordo', data_acordo = ?,
				valor_acordo = ?, data_vencimento = ?, valor = ?
			WHERE id = ? AND status IN (?, ?)
			""",
			(
				date.today().isoformat(),
				valor_acordo,
				data_acordo.isoformat(),
				valor_acordo,
				mensalidade_id,
				*STATUS_ABERTOS,
			),
		)
		if cursor.rowcount == 0:
			raise ValueError("A parcela selecionada nao esta aberta.")
		cursor.execute(
			"""
			UPDATE clientes
			SET status_pagamento = CASE
				WHEN EXISTS (
					SELECT 1 FROM mensalidades
					WHERE cliente_id = clientes.id
					  AND status = 'Atrasada'
				) THEN 'Atrasada'
				ELSE 'Em Acordo'
			END
			WHERE id = (SELECT cliente_id FROM mensalidades WHERE id = ?)
			""",
			(mensalidade_id,),
		)
		conexao.commit()
		return True
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
				nome_banco TEXT NOT NULL DEFAULT '',
				dias_cobranca_pre_vencimento INTEGER NOT NULL DEFAULT 2,
				intervalo_cobranca_pos_vencimento INTEGER NOT NULL DEFAULT 3
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
		for nome, padrao in (
			("dias_cobranca_pre_vencimento", 2),
			("intervalo_cobranca_pos_vencimento", 3),
		):
			if nome not in colunas:
				cursor.execute(
					f"ALTER TABLE configuracoes ADD COLUMN {nome} "
					f"INTEGER NOT NULL DEFAULT {padrao}"
				)
		cursor.execute(
			"""
			INSERT OR IGNORE INTO configuracoes
				(id, nome_empresa, chave_pix, nome_banco,
				 dias_cobranca_pre_vencimento,
				 intervalo_cobranca_pos_vencimento)
			VALUES (1, '', '', '', 2, 3)
			"""
		)
	finally:
		cursor.close()


def salvar_configuracoes(
	conexao,
	nome_empresa,
	chave_pix,
	nome_banco,
	dias_cobranca_pre_vencimento=2,
	intervalo_cobranca_pos_vencimento=3,
):
	"""Persiste os dados usados nas mensagens de cobranca."""
	cursor = conexao.cursor()
	try:
		cursor.execute(
			"""
			INSERT INTO configuracoes
				(id, nome_empresa, chave_pix, nome_banco,
				 dias_cobranca_pre_vencimento,
				 intervalo_cobranca_pos_vencimento)
			VALUES (1, ?, ?, ?, ?, ?)
			ON CONFLICT(id) DO UPDATE SET
				nome_empresa = excluded.nome_empresa,
				chave_pix = excluded.chave_pix,
				nome_banco = excluded.nome_banco,
				dias_cobranca_pre_vencimento =
					excluded.dias_cobranca_pre_vencimento,
				intervalo_cobranca_pos_vencimento =
					excluded.intervalo_cobranca_pos_vencimento
			""",
			(
				str(nome_empresa or "").strip(),
				str(chave_pix or "").strip(),
				str(nome_banco or "").strip(),
				_normalizar_dias_regua(dias_cobranca_pre_vencimento, "pre"),
				_normalizar_dias_regua(
					intervalo_cobranca_pos_vencimento, "pos"
				),
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
			SELECT nome_empresa, chave_pix, nome_banco,
				   dias_cobranca_pre_vencimento,
				   intervalo_cobranca_pos_vencimento
			FROM configuracoes
			WHERE id = ?
			""",
			(1,),
		)
		linha = cursor.fetchone()
		if linha is None:
			return {
				"nome_empresa": "",
				"chave_pix": "",
				"nome_banco": "",
				"dias_cobranca_pre_vencimento": 2,
				"intervalo_cobranca_pos_vencimento": 3,
			}
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
		cursor.execute(
			"UPDATE clientes SET status_pagamento = 'Atrasada' "
			"WHERE status_pagamento = 'Atrasado'"
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
				"Atrasada" if datas_atrasadas else "Pendente",
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
						"Atrasada",
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
					"Atrasada" if data_mensalidade < date.today() else "Pendente",
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
			(cliente_id, "Pendente", "Atrasada"),
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
						"Atrasada",
					),
				)
			status_cliente = "Atrasada"
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
					"Atrasada" if data_mensalidade < date.today() else "Pendente",
				),
			)
			status_cliente = (
				"Atrasada"
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
			cliente["status_pagamento"] not in ("Pago", "Em Acordo")
			and cliente["data_vencimento"] < hoje
		):
			cliente["status_pagamento"] = "Atrasada"

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

	Quando ``forcar`` e falso, respeita a regua configurada pela empresa.
	Parcelas em acordo nao aparecem nesta consulta e ficam sem alertas.
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
				mensalidade["status"] == "Pendente"
				and data_mensalidade < hoje
			):
				cursor = conexao.cursor()
				try:
					cursor.execute(
						"""
						UPDATE mensalidades
						SET status = 'Atrasada'
						WHERE id = ? AND status = 'Pendente'
						""",
						(mensalidade["id"],),
					)
					conexao.commit()
				finally:
					cursor.close()
				mensalidade["status"] = "Atrasada"

		ultimo_envio = cliente["ultimo_envio_cobranca"]
		if ultimo_envio is not None:
			ultimo_envio = date.fromisoformat(ultimo_envio)
		if forcar:
			mensalidades_cobranca = mensalidades_abertas
		else:
			dias_pre = configuracoes["dias_cobranca_pre_vencimento"]
			intervalo_pos = configuracoes[
				"intervalo_cobranca_pos_vencimento"
			]
			mensalidades_cobranca = []
			for mensalidade in mensalidades_abertas:
				data_mensalidade = date.fromisoformat(
					mensalidade["data_vencimento"]
				)
				if data_mensalidade >= hoje:
					if (data_mensalidade - hoje).days <= dias_pre:
						mensalidades_cobranca.append(mensalidade)
				elif ultimo_envio is None or (
					hoje - ultimo_envio
				).days >= intervalo_pos:
					mensalidades_cobranca.append(mensalidade)
			if not mensalidades_cobranca:
				continue
		deve_enviar = (
			forcar
			or ultimo_envio is None
			or (hoje - ultimo_envio).days >= configuracoes[
				"intervalo_cobranca_pos_vencimento"
			]
		)
		if not deve_enviar:
			continue

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
					(
						"Atrasada"
						if any(
							m["status"] == "Atrasada"
							for m in mensalidades_abertas
						)
						else "Pendente"
					),
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
