import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import re
import threading
import sqlite3
from datetime import datetime
import gestor

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
    self.lbl_datas_atrasadas = ctk.CTkLabel(
        self.aba_cliente,
        text="Datas/Vencimentos Atrasados (opcional):",
        anchor="w",
        font=ctk.CTkFont(size=12, weight="bold"),
    )
    self.lbl_datas_atrasadas.pack(fill="x", padx=15, pady=(4, 0))
    self.ent_datas_atrasadas = ctk.CTkEntry(
        self.aba_cliente,
        placeholder_text="Ex: 10/07/2026, 10/08/2026",
        height=30,
    )
    self.ent_datas_atrasadas.pack(fill="x", padx=15, pady=(2, 6))
    self.ent_datas_atrasadas.bind(
        "<KeyRelease>", self.formatar_datas_digitadas
    )
    for entrada in (
        self.ent_nome,
        self.ent_telefone,
        self.ent_valor,
        self.ent_vencimento,
        self.ent_datas_atrasadas,
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
    self.frame_tabela.grid_rowconfigure(1, weight=1)
    self.frame_tabela.grid_columnconfigure(0, weight=1)

    # Botões Superiores
    self.frame_acoes = ctk.CTkFrame(self.frame_tabela, fg_color="transparent")
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

    self.btn_pago = ctk.CTkButton(
        self.frame_acoes,
        text="✅ Marcar Pago",
        fg_color="#1f6aa5",
        width=130,
        command=self.marcar_como_pago,
    )
    self.btn_pago.pack(side="left", padx=5)

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
        self.frame_tabela, columns=colunas, show="headings"
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
    self.tree.tag_configure("Atrasado", foreground="#ff5c5c")
    self.tree.tag_configure("Pendente", foreground="#f5d76e")

    # Carregar Clientes na Tabela
    self.atualizar_tabela()
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

  def carregar_configuracoes(self):
    configuracoes = gestor.obter_configuracoes(self.conexao)
    campos = (
        (self.ent_nome_empresa, configuracoes["nome_empresa"]),
        (self.ent_chave_pix, configuracoes["chave_pix"]),
        (self.ent_nome_banco, configuracoes["nome_banco"]),
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
    datas_atrasadas = self.ent_datas_atrasadas.get().strip(", ")

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
            datas_atrasadas,
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
            datas_atrasadas,
        )
        mensagem = f"Cliente {nome} atualizado com sucesso!"
      messagebox.showinfo("Sucesso", mensagem)
      self.cancelar_edicao()
      self.atualizar_tabela()
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
    try:
      mensalidades = gestor.listar_mensalidades_abertas(
          self.conexao, self.cliente_em_edicao
      )
      datas = [
          datetime.strptime(
              mensalidade["data_vencimento"], "%Y-%m-%d"
          ).strftime("%d/%m/%Y")
          for mensalidade in mensalidades
      ]
      self.ent_datas_atrasadas.delete(0, "end")
      self.ent_datas_atrasadas.insert(0, ", ".join(datas))
    except sqlite3.Error as erro:
      messagebox.showerror("Erro no banco de dados", str(erro))
      return
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
        self.ent_datas_atrasadas,
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
    janela.geometry("420x420")
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
        gestor.dar_baixa_mensalidades(self.conexao, ids)
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