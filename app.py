import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import re
import threading
import sqlite3
from datetime import datetime
import gestor

# Copyright (c) 2026 Marcio Ramos. Todos os direitos reservados.
# Configuração do tema do CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def formatar_valor_moeda(texto):
  """Formata os digitos informados como reais, usando os dois ultimos como centavos."""
  digitos = re.sub(r"\D", "", texto)
  if not digitos:
    return ""

  digitos = digitos.lstrip("0") or "0"
  if len(digitos) == 1:
    digitos = f"0{digitos}"
  parte_inteira = digitos[:-2].lstrip("0") or "0"
  centavos = digitos[-2:]
  return f"{parte_inteira},{centavos}"


class AppGestor(ctk.CTk):

  def __init__(self):
    super().__init__()

    # Configurações da Janela
    self.title("Gestor de Clientes & Cobranças WhatsApp")
    self.geometry("1150x700")
    self.minsize(1050, 650)

    # Conexão com o Banco SQLite
    self.conexao = gestor.conectar_banco()
    self.cliente_em_edicao = None

    # Layout Principal (Grid 2 Colunas)
    self.grid_columnconfigure(1, weight=1)
    self.grid_rowconfigure(0, weight=1)
    self.grid_rowconfigure(1, weight=0)

    # ================= PAINEL ESQUERDO =================
    self.frame_form = ctk.CTkTabview(self, width=290)
    self.frame_form.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
    self.frame_form.add("👤 Cliente")
    self.frame_form.add("⚙️ Configurações")
    self.aba_cliente = self.frame_form.tab("👤 Cliente")
    self.aba_configuracoes = self.frame_form.tab("⚙️ Configurações")

    self.lbl_titulo = ctk.CTkLabel(
        self.aba_cliente,
        text="Cadastrar Cliente",
        font=ctk.CTkFont(size=18, weight="bold"),
    )
    self.lbl_titulo.pack(pady=(12, 8))

    self.lbl_nome = ctk.CTkLabel(
        self.aba_cliente,
        text="Nome Completo:",
        anchor="w",
        font=ctk.CTkFont(size=12, weight="bold"),
    )
    self.lbl_nome.pack(fill="x", padx=15, pady=(4, 0))
    self.ent_nome = ctk.CTkEntry(
        self.aba_cliente, placeholder_text="Ex: João Silva", height=30
    )
    self.ent_nome.pack(fill="x", padx=15, pady=(2, 6))

    self.lbl_telefone = ctk.CTkLabel(
        self.aba_cliente,
        text="Telefone (WhatsApp):",
        anchor="w",
        font=ctk.CTkFont(size=12, weight="bold"),
    )
    self.lbl_telefone.pack(fill="x", padx=15, pady=(4, 0))
    self.ent_telefone = ctk.CTkEntry(
        self.aba_cliente,
        placeholder_text="Ex: 85999998888",
        height=30,
    )
    self.ent_telefone.pack(fill="x", padx=15, pady=(2, 6))

    self.lbl_valor = ctk.CTkLabel(
        self.aba_cliente,
        text="Valor da Mensalidade (R$):",
        anchor="w",
        font=ctk.CTkFont(size=12, weight="bold"),
    )
    self.lbl_valor.pack(fill="x", padx=15, pady=(4, 0))
    self.ent_valor = ctk.CTkEntry(
        self.aba_cliente,
        placeholder_text="Ex: 150,00",
        height=30,
    )
    self.ent_valor.pack(fill="x", padx=15, pady=(2, 6))
    self.ent_valor.bind(
        "<KeyRelease>", self.formatar_valor_digitado
    )

    self.lbl_vencimento = ctk.CTkLabel(
        self.aba_cliente,
        text="Dia do Vencimento (1 a 31):",
        anchor="w",
        font=ctk.CTkFont(size=12, weight="bold"),
    )
    self.lbl_vencimento.pack(fill="x", padx=15, pady=(4, 0))
    self.ent_vencimento = ctk.CTkEntry(
        self.aba_cliente,
        placeholder_text="Ex: 10",
        height=30,
    )
    self.ent_vencimento.pack(fill="x", padx=15, pady=(2, 6))
    for entrada in (
        self.ent_nome,
        self.ent_telefone,
        self.ent_valor,
        self.ent_vencimento,
    ):
      entrada.bind(
          "<KeyRelease>", self.verificar_formulario_limpo, add="+"
      )

    self.btn_cadastrar = ctk.CTkButton(
        self.aba_cliente,
        text="➕ Cadastrar",
        fg_color="#2ba84a",
        hover_color="#1e7a35",
        command=self.cadastrar_cliente,
    )
    self.btn_cadastrar.pack(fill="x", padx=15, pady=(8, 6))

    self.btn_cancelar = ctk.CTkButton(
        self.aba_cliente,
        text="Cancelar edição",
        fg_color="#666666",
        hover_color="#4d4d4d",
        command=self.cancelar_edicao,
        state="disabled",
    )
    self.btn_cancelar.pack(fill="x", padx=15, pady=(0, 8))

    self.lbl_config = ctk.CTkLabel(
        self.aba_configuracoes,
        text="Dados da Empresa & PIX",
        font=ctk.CTkFont(size=15, weight="bold"),
    )
    self.lbl_config.pack(pady=(12, 4))

    self.lbl_nome_empresa = ctk.CTkLabel(
        self.aba_configuracoes,
        text="Nome da Empresa:",
        font=ctk.CTkFont(size=11, weight="bold"),
    )
    self.lbl_nome_empresa.pack(anchor="w", padx=15, pady=(2, 0))
    self.ent_nome_empresa = ctk.CTkEntry(
        self.aba_configuracoes,
        placeholder_text="Empresa",
        height=30,
    )
    self.ent_nome_empresa.pack(fill="x", padx=15, pady=(2, 4))

    self.lbl_chave_pix = ctk.CTkLabel(
        self.aba_configuracoes,
        text="Chave PIX:",
        font=ctk.CTkFont(size=11, weight="bold"),
    )
    self.lbl_chave_pix.pack(anchor="w", padx=15, pady=(2, 0))
    self.ent_chave_pix = ctk.CTkEntry(
        self.aba_configuracoes,
        placeholder_text="Chave Pix",
        height=30,
    )
    self.ent_chave_pix.pack(fill="x", padx=15, pady=(2, 4))

    self.lbl_nome_banco = ctk.CTkLabel(
        self.aba_configuracoes,
        text="Banco / Favorecido:",
        font=ctk.CTkFont(size=11, weight="bold"),
    )
    self.lbl_nome_banco.pack(anchor="w", padx=15, pady=(2, 0))
    self.ent_nome_banco = ctk.CTkEntry(
        self.aba_configuracoes,
        placeholder_text="Banco",
        height=30,
    )
    self.ent_nome_banco.pack(fill="x", padx=15, pady=(2, 4))

    self.lbl_dias_pre = ctk.CTkLabel(
        self.aba_configuracoes,
        text="Dias para cobrança pré-vencimento:",
        font=ctk.CTkFont(size=11, weight="bold"),
    )
    self.lbl_dias_pre.pack(anchor="w", padx=15, pady=(2, 0))
    self.ent_dias_pre = ctk.CTkEntry(
        self.aba_configuracoes, placeholder_text="Ex: 2", height=30
    )
    self.ent_dias_pre.pack(fill="x", padx=15, pady=(2, 4))

    self.lbl_intervalo_pos = ctk.CTkLabel(
        self.aba_configuracoes,
        text="Intervalo pós-vencimento (dias):",
        font=ctk.CTkFont(size=11, weight="bold"),
    )
    self.lbl_intervalo_pos.pack(anchor="w", padx=15, pady=(2, 0))
    self.ent_intervalo_pos = ctk.CTkEntry(
        self.aba_configuracoes, placeholder_text="Ex: 3", height=30
    )
    self.ent_intervalo_pos.pack(fill="x", padx=15, pady=(2, 4))

    self.btn_salvar_configuracoes = ctk.CTkButton(
        self.aba_configuracoes,
        text="💾 Salvar Configurações",
        command=self.salvar_configuracoes,
    )
    self.btn_salvar_configuracoes.pack(fill="x", padx=15, pady=(8, 10))

    self.btn_limpar_configuracoes = ctk.CTkButton(
        self.aba_configuracoes,
        text="🗑️ Limpar Configurações",
        fg_color="#d90429",
        hover_color="#9e021b",
        command=self.limpar_configuracoes,
    )
    self.btn_limpar_configuracoes.pack(fill="x", padx=15, pady=10)

    # ================= PAINEL DIREITO (TABELA E AÇÕES) =================
    self.frame_tabela = ctk.CTkFrame(self, corner_radius=10)
    self.frame_tabela.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")
    self.frame_tabela.grid_rowconfigure(0, weight=1)
    self.frame_tabela.grid_columnconfigure(0, weight=1)
    self.abas_financeiras = ctk.CTkTabview(self.frame_tabela)
    self.abas_financeiras.grid(row=0, column=0, sticky="nsew")
    self.abas_financeiras.add("Clientes")
    self.abas_financeiras.add("Parcelas")
    self.aba_clientes = self.abas_financeiras.tab("Clientes")
    self.aba_parcelas = self.abas_financeiras.tab("Parcelas")
    self.aba_clientes.grid_rowconfigure(1, weight=1)
    self.aba_clientes.grid_columnconfigure(0, weight=1)
    self.aba_parcelas.grid_rowconfigure(4, weight=1)
    self.aba_parcelas.grid_columnconfigure(0, weight=1)

    # Botões Superiores
    self.frame_acoes = ctk.CTkFrame(self.aba_clientes, fg_color="transparent")
    self.frame_acoes.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

    self.btn_cobrancas = ctk.CTkButton(
        self.frame_acoes,
        text="🚀 Disparar Cobranças (WhatsApp)",
        fg_color="#25D366",
        text_color="black",
        hover_color="#1da851",
        width=220,
        command=self.disparar_cobrancas,
    )
    self.btn_cobrancas.pack(side="left", padx=5)

    self.btn_editar = ctk.CTkButton(
        self.frame_acoes,
        text="✏️ Editar",
        fg_color="#d98e04",
        hover_color="#a96e03",
        width=110,
        command=self.editar_cliente,
    )
    self.btn_editar.pack(side="left", padx=5)

    self.btn_excluir = ctk.CTkButton(
        self.frame_acoes,
        text="🗑️ Excluir",
        fg_color="#d90429",
        hover_color="#9e021b",
        width=110,
        command=self.excluir_cliente,
    )
    self.btn_excluir.pack(side="left", padx=5)

    # Estilização da Tabela Treeview (Modo Escuro)
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Treeview",
        background="#2a2d2e",
        foreground="white",
        fieldbackground="#2a2d2e",
        rowheight=28,
    )
    style.map("Treeview", background=[("selected", "#1f6aa5")])

    # Tabela
    colunas = ("id", "nome", "telefone", "valor", "vencimento", "status")
    self.tree = ttk.Treeview(
        self.aba_clientes, columns=colunas, show="headings"
    )

    self.tree.heading("id", text="ID")
    self.tree.heading("nome", text="Nome")
    self.tree.heading("telefone", text="Telefone")
    self.tree.heading("valor", text="Valor (R$)")
    self.tree.heading("vencimento", text="Vencimento")
    self.tree.heading("status", text="Status")

    self.tree.column("id", width=40, anchor="center")
    self.tree.column("nome", width=180)
    self.tree.column("telefone", width=110)
    self.tree.column("valor", width=90, anchor="e")
    self.tree.column("vencimento", width=100, anchor="center")
    self.tree.column("status", width=90, anchor="center")

    self.tree.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
    self.tree.tag_configure("Pago", foreground="#55d66b")
    self.tree.tag_configure("Atrasada", foreground="#ff5c5c")
    self.tree.tag_configure("Em Acordo", foreground="#c58cff")
    self.tree.tag_configure("Adiantada", foreground="#62d9d9")
    self.tree.tag_configure("Pendente", foreground="#f5d76e")

    self.lbl_parcelas = ctk.CTkLabel(
        self.aba_parcelas,
        text="Gestão de Parcelas e Status",
        font=ctk.CTkFont(size=17, weight="bold"),
    )
    self.lbl_parcelas.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="w")
    self.clientes_parcelas = {}
    self.filtro_cliente_parcelas = tk.StringVar(
        value="Todos os Clientes"
    )
    self.menu_cliente_parcelas = ctk.CTkOptionMenu(
        self.aba_parcelas,
        variable=self.filtro_cliente_parcelas,
        values=["Todos os Clientes"],
        command=self.filtrar_parcelas_por_cliente,
    )
    self.menu_cliente_parcelas.grid(
        row=1, column=0, padx=12, pady=(0, 8), sticky="w"
    )
    self.frame_inserir_parcela = ctk.CTkFrame(
        self.aba_parcelas, fg_color="transparent"
    )
    self.frame_inserir_parcela.grid(
        row=2, column=0, padx=10, pady=(0, 8), sticky="ew"
    )
    self.ent_data_parcela = ctk.CTkEntry(
        self.frame_inserir_parcela,
        placeholder_text="Data (DD/MM/AAAA)",
        width=170,
    )
    self.ent_data_parcela.pack(side="left", padx=4)
    self.ent_data_parcela.bind(
        "<KeyRelease>", self.formatar_data_parcela
    )
    self.ent_valor_parcela = ctk.CTkEntry(
        self.frame_inserir_parcela,
        placeholder_text="Valor (R$)",
        width=120,
    )
    self.ent_valor_parcela.pack(side="left", padx=4)
    self.ent_valor_parcela.bind(
        "<KeyRelease>", self.formatar_valor_parcela
    )
    self.btn_inserir_parcela = ctk.CTkButton(
        self.frame_inserir_parcela,
        text="+ Inserir parcela",
        fg_color="#1f6aa5",
        hover_color="#144870",
        width=140,
        command=self.inserir_parcela,
        state="disabled",
    )
    self.btn_inserir_parcela.pack(side="left", padx=4)
    self.filtro_parcelas = tk.StringVar(value="Pendente")
    self.frame_filtros_parcelas = ctk.CTkFrame(
        self.aba_parcelas, fg_color="transparent"
    )
    self.frame_filtros_parcelas.grid(
        row=3, column=0, padx=10, pady=(0, 8), sticky="ew"
    )
    for texto in ("Todas", "Pendente", "Atrasada", "Paga", "Em Acordo"):
      ctk.CTkRadioButton(
          self.frame_filtros_parcelas,
          text=texto,
          variable=self.filtro_parcelas,
          value=texto,
          command=self.atualizar_tabela_parcelas,
      ).pack(side="left", padx=8)
    colunas_parcelas = (
        "id", "cliente", "referencia", "vencimento", "valor", "status"
    )
    self.tree_parcelas = ttk.Treeview(
        self.aba_parcelas, columns=colunas_parcelas, show="headings"
    )
    for coluna, titulo, largura in (
        ("id", "ID", 55),
        ("cliente", "Cliente", 220),
        ("referencia", "Referência", 110),
        ("vencimento", "Vencimento", 110),
        ("valor", "Valor (R$)", 110),
        ("status", "Status", 120),
    ):
      self.tree_parcelas.heading(coluna, text=titulo)
      self.tree_parcelas.column(
          coluna, width=largura,
          anchor="e" if coluna == "valor" else "center"
      )
    self.tree_parcelas.grid(
        row=4, column=0, padx=10, pady=(0, 10), sticky="nsew"
    )
    self.tree_parcelas.tag_configure("Atrasada", foreground="#ff5c5c")
    self.tree_parcelas.tag_configure("Pendente", foreground="#f5d76e")
    self.tree_parcelas.tag_configure("Pago", foreground="#55d66b")
    self.tree_parcelas.tag_configure("Adiantada", foreground="#62d9d9")
    self.tree_parcelas.tag_configure("Em Acordo", foreground="#c58cff")
    self.tree_parcelas.bind("<Double-1>", self.alterar_status_parcela)

    self.frame_rodape = ctk.CTkFrame(self, fg_color="transparent", height=24)
    self.frame_rodape.grid(
        row=1, column=0, columnspan=2, padx=15, pady=(0, 5), sticky="ew"
    )
    self.lbl_assinatura = ctk.CTkLabel(
        self.frame_rodape,
        text="v1.0.0 | Dev: Marcio Ramos",
        font=ctk.CTkFont(size=9),
        text_color="#505050",
    )
    self.lbl_assinatura.pack(side="right", padx=4)

    # Carregar Clientes na Tabela
    self.atualizar_tabela()
    self.carregar_clientes_parcelas()
    self.atualizar_tabela_parcelas()
    self.update()
    self.after(100, self.carregar_configuracoes)

  def atualizar_tabela(self):
    """Limpa e recarrega os dados da tabela vindos do banco."""
    for item in self.tree.get_children():
      self.tree.delete(item)

    clientes = gestor.listar_clientes(self.conexao)
    for c in clientes:
      venc = f"Todo dia {c['data_vencimento'].day}"
      valor = f"{c['valor_mensalidade']:.2f}".replace(".", ",")
      self.tree.insert(
          "",
          "end",
          values=(
              c["id"],
              c["nome"],
              c["telefone"],
              f"R$ {valor}",
              venc,
              c["status_pagamento"],
          ),
          tags=(c["status_pagamento"],),
      )

  def atualizar_tabela_parcelas(self):
    """Atualiza a lista financeira conforme o chip de status selecionado."""
    for item in self.tree_parcelas.get_children():
      self.tree_parcelas.delete(item)
    try:
      parcelas = gestor.listar_parcelas(
          self.conexao,
          self.filtro_parcelas.get(),
          self.clientes_parcelas.get(
              self.filtro_cliente_parcelas.get()
          ),
      )
    except (sqlite3.Error, ValueError) as erro:
      messagebox.showerror("Erro ao carregar parcelas", str(erro))
      return
    for parcela in parcelas:
      vencimento = datetime.strptime(
          parcela["data_vencimento"], "%Y-%m-%d"
      ).strftime("%d/%m/%Y")
      valor = f"R$ {parcela['valor']:.2f}".replace(".", ",")
      self.tree_parcelas.insert(
          "",
          "end",
          values=(
              parcela["id"],
              parcela["cliente_nome"],
              parcela["mes_referencia"],
              vencimento,
              valor,
              parcela["status"],
          ),
          tags=(parcela["status"],),
      )

  def carregar_clientes_parcelas(self):
    """Carrega o menu com todos os clientes e preserva a seleção atual."""
    try:
      clientes = gestor.listar_clientes_filtro(self.conexao)
    except sqlite3.Error as erro:
      messagebox.showerror("Erro ao carregar clientes", str(erro))
      return
    self.clientes_parcelas = {"Todos os Clientes": None}
    for cliente in clientes:
      exibicao = f"{cliente['nome']} (ID {cliente['id']})"
      self.clientes_parcelas[exibicao] = cliente["id"]
    valores = list(self.clientes_parcelas)
    selecao_atual = self.filtro_cliente_parcelas.get()
    if selecao_atual not in self.clientes_parcelas:
      selecao_atual = "Todos os Clientes"
      self.filtro_cliente_parcelas.set(selecao_atual)
    self.menu_cliente_parcelas.configure(
        values=valores,
        variable=self.filtro_cliente_parcelas,
    )
    self.filtrar_parcelas_por_cliente()

  def filtrar_parcelas_por_cliente(self, _cliente_selecionado=None):
    """Filtra a tabela pela combinação de cliente e status selecionados."""
    cliente_id = self.clientes_parcelas.get(
        self.filtro_cliente_parcelas.get()
    )
    self.btn_inserir_parcela.configure(
        state="normal" if cliente_id is not None else "disabled"
    )
    self.atualizar_tabela_parcelas()

  def inserir_parcela(self):
    """Insere uma parcela apenas para o cliente escolhido."""
    cliente_id = self.clientes_parcelas.get(
        self.filtro_cliente_parcelas.get()
    )
    if cliente_id is None:
      messagebox.showwarning(
          "Cliente obrigatorio",
          "Selecione um cliente antes de inserir uma parcela.",
      )
      return
    data_vencimento = self.ent_data_parcela.get().strip()
    campos = (data_vencimento, self.ent_valor_parcela.get().strip())
    if not all(campos):
      messagebox.showwarning(
          "Campos obrigatorios",
          "Preencha data e valor da parcela.",
      )
      return
    try:
      mes_referencia = datetime.strptime(
          data_vencimento, "%d/%m/%Y"
      ).strftime("%m/%Y")
      gestor.inserir_parcela(
          self.conexao,
          cliente_id,
          mes_referencia,
          self.ent_valor_parcela.get(),
          data_vencimento,
      )
    except (sqlite3.Error, ValueError) as erro:
      messagebox.showerror("Erro ao inserir parcela", str(erro))
      return
    self.ent_valor_parcela.delete(0, "end")
    self.ent_data_parcela.delete(0, "end")
    self.atualizar_tabela_parcelas()
    self.atualizar_tabela()
    messagebox.showinfo("Sucesso", "Parcela inserida sem alterar o historico.")

  def _substituir_texto_mascarado(self, entrada, texto):
    """Atualiza uma entrada mascarada sem reprocessar o proprio evento."""
    if getattr(self, "_formatando_parcela", False):
      return
    if entrada.get() == texto:
      return
    self._formatando_parcela = True
    try:
      entrada.delete(0, "end")
      entrada.insert(0, texto)
      entrada.icursor("end")
    finally:
      self._formatando_parcela = False

  def formatar_data_parcela(self, _evento=None):
    """Mascara a data da parcela no formato DD/MM/AAAA."""
    digitos = re.sub(r"\D", "", self.ent_data_parcela.get())[:8]
    texto = digitos
    if len(digitos) > 4:
      texto = f"{digitos[:2]}/{digitos[2:4]}/{digitos[4:]}"
    elif len(digitos) > 2:
      texto = f"{digitos[:2]}/{digitos[2:]}"
    self._substituir_texto_mascarado(self.ent_data_parcela, texto)

  def formatar_valor_parcela(self, _evento=None):
    """Mascara o valor da parcela como reais com duas casas decimais."""
    texto = formatar_valor_moeda(self.ent_valor_parcela.get())
    self._substituir_texto_mascarado(self.ent_valor_parcela, texto)

  def alterar_status_parcela(self, _evento=None):
    """Altera o status da parcela selecionada e persiste imediatamente."""
    selecionado = self.tree_parcelas.selection()
    if not selecionado:
      return
    item = self.tree_parcelas.item(selecionado[0])
    status_atual = str(item["values"][5])
    if status_atual in ("Pago", "Adiantada"):
      status_atual = "Paga"
    janela = ctk.CTkToplevel(self)
    janela.title("Alterar status da parcela")
    janela.geometry("320x190")
    janela.transient(self)
    janela.grab_set()
    ctk.CTkLabel(
        janela, text="Novo status:", font=ctk.CTkFont(size=14, weight="bold")
    ).pack(pady=(20, 8))
    status = tk.StringVar(value=status_atual)
    ctk.CTkOptionMenu(
        janela,
        variable=status,
        values=["Pendente", "Atrasada", "Paga", "Em Acordo"],
    ).pack(fill="x", padx=30, pady=4)

    def salvar_status():
      try:
        gestor.atualizar_status_mensalidade(
            self.conexao, int(item["values"][0]), status.get()
        )
      except (sqlite3.Error, ValueError) as erro:
        messagebox.showerror(
            "Erro ao atualizar status", str(erro), parent=janela
        )
        return
      janela.grab_release()
      janela.destroy()
      self.atualizar_tabela_parcelas()
      self.atualizar_tabela()

    ctk.CTkButton(
        janela, text="Salvar status", command=salvar_status
    ).pack(fill="x", padx=30, pady=(10, 15))

  def carregar_configuracoes(self):
    configuracoes = gestor.obter_configuracoes(self.conexao)
    campos = (
        (self.ent_nome_empresa, configuracoes["nome_empresa"]),
        (self.ent_chave_pix, configuracoes["chave_pix"]),
        (self.ent_nome_banco, configuracoes["nome_banco"]),
        (
            self.ent_dias_pre,
            configuracoes["dias_cobranca_pre_vencimento"],
        ),
        (
            self.ent_intervalo_pos,
            configuracoes["intervalo_cobranca_pos_vencimento"],
        ),
    )
    for entrada, valor in campos:
      entrada.delete(0, "end")
      if valor:
        entrada.insert(0, valor)
    self.update_idletasks()

  def salvar_configuracoes(self):
    try:
      gestor.salvar_configuracoes(
          self.conexao,
          self.ent_nome_empresa.get(),
          self.ent_chave_pix.get(),
          self.ent_nome_banco.get(),
          self.ent_dias_pre.get(),
          self.ent_intervalo_pos.get(),
      )
      messagebox.showinfo(
          "Sucesso", "Configurações salvas com sucesso!"
      )
    except (sqlite3.Error, ValueError) as erro:
      messagebox.showerror("Erro no banco de dados", str(erro))

  def limpar_configuracoes(self):
    confirmado = messagebox.askyesno(
        "Confirmação",
        "Deseja realmente excluir/limpar as configurações da empresa?",
    )
    if not confirmado:
      return

    try:
      gestor.limpar_configuracoes(self.conexao)
      for entrada in (
          self.ent_nome_empresa,
          self.ent_chave_pix,
          self.ent_nome_banco,
          self.ent_dias_pre,
          self.ent_intervalo_pos,
      ):
        entrada.delete(0, "end")
      messagebox.showinfo(
          "Sucesso", "Configurações excluídas com sucesso!"
      )
    except (sqlite3.Error, ValueError) as erro:
      messagebox.showerror("Erro no banco de dados", str(erro))

  def formatar_valor_digitado(self, _evento=None):
    """Aplica a mascara de moeda enquanto o usuario digita."""
    valor_formatado = formatar_valor_moeda(self.ent_valor.get())
    if valor_formatado == self.ent_valor.get():
      return
    self.ent_valor.delete(0, "end")
    self.ent_valor.insert(0, valor_formatado)
    self.ent_valor.icursor("end")

  def formatar_datas_digitadas(self, _evento=None):
    """Aplica a mascara DD/MM/AAAA para uma lista de datas."""
    texto_atual = self.ent_datas_atrasadas.get()
    digitos = re.sub(r"\D", "", texto_atual)
    if not digitos:
      if texto_atual:
        self.ent_datas_atrasadas.delete(0, "end")
      return

    datas_completas = []
    while len(digitos) >= 8:
      bloco = digitos[:8]
      digitos = digitos[8:]
      datas_completas.append(
          f"{bloco[:2]}/{bloco[2:4]}/{bloco[4:]}"
      )

    partes = datas_completas
    if digitos:
      if len(digitos) <= 2:
        parcial = digitos
      elif len(digitos) <= 4:
        parcial = f"{digitos[:2]}/{digitos[2:]}"
      else:
        parcial = f"{digitos[:2]}/{digitos[2:4]}/{digitos[4:]}"
      partes.append(parcial)

    formatado = ", ".join(partes)
    if datas_completas and not digitos:
      formatado += ", "

    if formatado != texto_atual:
      self.ent_datas_atrasadas.delete(0, "end")
      self.ent_datas_atrasadas.insert(0, formatado)
    self.ent_datas_atrasadas.icursor("end")

  def verificar_formulario_limpo(self, _evento=None):
    if self.cliente_em_edicao is None:
      return
    entradas = (
        self.ent_nome,
        self.ent_telefone,
        self.ent_valor,
        self.ent_vencimento,
    )
    if all(not entrada.get().strip() for entrada in entradas):
      self.cancelar_edicao()

  def cadastrar_cliente(self):
    nome = self.ent_nome.get().strip()
    telefone = self.ent_telefone.get().strip()
    valor = self.ent_valor.get().strip()
    venc_str = self.ent_vencimento.get().strip()
    if not (nome and telefone and valor and venc_str):
      messagebox.showwarning("Aviso", "Preencha todos os campos!")
      return

    try:
      if self.cliente_em_edicao is None:
        gestor.cadastrar_cliente(
            self.conexao,
            nome,
            telefone,
            valor,
            venc_str,
        )
        mensagem = f"Cliente {nome} cadastrado com sucesso!"
      else:
        gestor.atualizar_cliente(
            self.conexao,
            self.cliente_em_edicao,
            nome,
            telefone,
            valor,
            venc_str,
        )
        mensagem = f"Cliente {nome} atualizado com sucesso!"
      messagebox.showinfo("Sucesso", mensagem)
      self.cancelar_edicao()
      self.atualizar_tabela()
      self.carregar_clientes_parcelas()
      self.atualizar_tabela_parcelas()
    except ValueError as erro:
      messagebox.showerror("Dados invalidos", str(erro))
    except sqlite3.Error as erro:
      messagebox.showerror("Erro no banco de dados", str(erro))

  def editar_cliente(self):
    selecionado = self.tree.selection()
    if not selecionado:
      messagebox.showwarning(
          "Aviso", "Selecione um cliente na tabela para editar."
      )
      return

    item = self.tree.item(selecionado[0])
    valores = item["values"]
    self.cliente_em_edicao = int(valores[0])
    self.ent_nome.delete(0, "end")
    self.ent_nome.insert(0, valores[1])
    self.ent_telefone.delete(0, "end")
    self.ent_telefone.insert(0, valores[2])
    self.ent_valor.delete(0, "end")
    self.ent_valor.insert(0, formatar_valor_moeda(str(valores[3])))
    self.ent_vencimento.delete(0, "end")
    self.ent_vencimento.insert(0, str(self._dia_do_valor(valores[4])))
    self.btn_cadastrar.configure(text="💾 Salvar Alterações")
    self.btn_cancelar.configure(state="normal")

  @staticmethod
  def _dia_do_valor(valor):
    texto = str(valor)
    if texto.isdigit():
      return texto
    return texto.split()[-1]

  def cancelar_edicao(self):
    self.cliente_em_edicao = None
    for entrada in (
        self.ent_nome,
        self.ent_telefone,
        self.ent_valor,
        self.ent_vencimento,
    ):
      entrada.delete(0, "end")
    self.btn_cadastrar.configure(text="➕ Cadastrar")
    self.btn_cancelar.configure(state="disabled")

  def marcar_como_pago(self):
    selecionado = self.tree.selection()
    if not selecionado:
      messagebox.showwarning("Aviso", "Selecione um cliente na tabela!")
      return

    item = self.tree.item(selecionado[0])
    cliente_id = item["values"][0]
    try:
      mensalidades = gestor.listar_mensalidades_abertas(
          self.conexao, cliente_id
      )
    except sqlite3.Error as erro:
      messagebox.showerror("Erro no banco de dados", str(erro))
      return

    if not mensalidades:
      messagebox.showinfo(
          "Mensalidades",
          "Este cliente não possui mensalidades em aberto.",
      )
      return

    janela = ctk.CTkToplevel(self)
    janela.title("Baixa de mensalidades")
    janela.geometry("420x480")
    janela.transient(self)
    janela.grab_set()
    self.janela_baixa = janela

    ctk.CTkLabel(
        janela,
        text=f"Mensalidades em aberto - {item['values'][1]}",
        font=ctk.CTkFont(size=16, weight="bold"),
    ).pack(padx=20, pady=(20, 12))

    frame_lista = ctk.CTkScrollableFrame(janela, height=250)
    frame_lista.pack(fill="both", expand=True, padx=20, pady=(0, 12))
    selecoes = []
    for mensalidade in mensalidades:
      variavel = tk.BooleanVar(value=False)
      checkbox = ctk.CTkCheckBox(
          frame_lista,
          text=(
              f"{mensalidade['mes_referencia']} - "
              f"R$ {mensalidade['valor']:.2f} "
              f"({mensalidade['status']})"
          ),
          variable=variavel,
      )
      checkbox.pack(anchor="w", padx=10, pady=6)
      selecoes.append((mensalidade["id"], variavel))

    ctk.CTkLabel(
        janela, text="Desconto para pagamento adiantado (R$), opcional:"
    ).pack(anchor="w", padx=20)
    ent_desconto = ctk.CTkEntry(
        janela, placeholder_text="Ex: 10,00", height=30
    )
    ent_desconto.pack(fill="x", padx=20, pady=(2, 10))

    def confirmar_baixa():
      ids = [identificador for identificador, variavel in selecoes
             if variavel.get()]
      if not ids:
        messagebox.showwarning(
            "Aviso",
            "Selecione ao menos uma mensalidade para dar baixa.",
            parent=janela,
        )
        return
      try:
        gestor.dar_baixa_mensalidades(
            self.conexao, ids, ent_desconto.get() or 0
        )
      except (sqlite3.Error, ValueError) as erro:
        messagebox.showerror(
            "Erro ao registrar pagamento", str(erro), parent=janela
        )
        return
      janela.grab_release()
      janela.destroy()
      self.janela_baixa = None
      self.atualizar_tabela()
      messagebox.showinfo(
          "Sucesso",
          "Pagamento das mensalidades selecionadas registrado com sucesso!",
      )

    ctk.CTkButton(
        janela,
        text="Confirmar Pagamento dos Selecionados",
        command=confirmar_baixa,
    ).pack(fill="x", padx=20, pady=(0, 20))

  def registrar_acordo(self):
    """Abre um acordo para a primeira parcela aberta do cliente selecionado."""
    selecionado = self.tree.selection()
    if not selecionado:
      messagebox.showwarning("Aviso", "Selecione um cliente na tabela!")
      return
    cliente_id = self.tree.item(selecionado[0])["values"][0]
    mensalidades = gestor.listar_mensalidades_abertas(
        self.conexao, cliente_id
    )
    if not mensalidades:
      messagebox.showinfo("Mensalidades", "Não há parcelas abertas.")
      return
    parcela = mensalidades[0]
    nova_data = ctk.CTkInputDialog(
        text="Nova data (DD/MM/AAAA):", title="Renegociar parcela"
    ).get_input()
    novo_valor = ctk.CTkInputDialog(
        text="Novo valor (R$):", title="Renegociar parcela"
    ).get_input()
    if not nova_data or not novo_valor:
      return
    try:
      gestor.registrar_acordo(
          self.conexao, parcela["id"], nova_data, novo_valor
      )
      self.atualizar_tabela()
      messagebox.showinfo(
          "Sucesso",
          "Parcela colocada em acordo; os alertas antigos foram congelados.",
      )
    except (sqlite3.Error, ValueError) as erro:
      messagebox.showerror("Erro ao registrar acordo", str(erro))

  def excluir_cliente(self):
    selecionado = self.tree.selection()
    if not selecionado:
      messagebox.showwarning("Aviso", "Selecione um cliente na tabela!")
      return

    item = self.tree.item(selecionado[0])
    cliente_id = item["values"][0]
    nome = item["values"][1]

    if messagebox.askyesno(
        "Confirmação", f"Tem certeza que deseja excluir {nome}?"
    ):
      try:
        gestor.excluir_cliente(self.conexao, cliente_id)
        messagebox.showinfo("Sucesso", "Cliente excluído com sucesso!")
        self.atualizar_tabela()
        self.carregar_clientes_parcelas()
        self.atualizar_tabela_parcelas()
      except (sqlite3.Error, ValueError) as erro:
        messagebox.showerror("Erro no banco de dados", str(erro))

  def disparar_cobrancas(self):
    if self.btn_cobrancas.cget("state") == "disabled":
      return
    configuracoes = gestor.obter_configuracoes(self.conexao)
    if (
        not configuracoes["nome_empresa"].strip()
        or not configuracoes["chave_pix"].strip()
    ):
      messagebox.showwarning(
          "Configuração necessária",
          "Preencha o Nome da Empresa e a Chave PIX antes de "
          "disparar cobranças.",
      )
      return
    messagebox.showinfo(
        "WhatsApp",
        "O disparo manual será iniciado para os clientes em aberto. "
        "Mantenha o navegador aberto!",
    )
    self.btn_cobrancas.configure(state="disabled")
    threading.Thread(
        target=self._executar_cobrancas_em_background,
        daemon=True,
    ).start()

  def _executar_cobrancas_em_background(self):
    conexao = None
    try:
      conexao = gestor.conectar_banco()
      quantidade = gestor.gerar_cobrancas(conexao, forcar=True)
      self.after(0, self._finalizar_cobrancas, quantidade, None)
    except (sqlite3.Error, ValueError) as erro:
      self.after(0, self._finalizar_cobrancas, 0, erro)
    finally:
      if conexao is not None:
        conexao.close()

  def _finalizar_cobrancas(self, quantidade, erro):
    self.btn_cobrancas.configure(state="normal")
    if erro is not None:
      messagebox.showerror("Erro ao gerar cobranças", str(erro))
      return
    messagebox.showinfo(
        "Concluído",
        f"{quantidade} cobrança(s) processada(s).",
    )
    self.atualizar_tabela()


if __name__ == "__main__":
  app = AppGestor()
  app.mainloop()