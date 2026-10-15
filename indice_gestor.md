# Índice de `gestor.py`

| Número da Linha | Nome da Função / Classe / Módulo | Descrição resumida do que faz |
| --- | --- | --- |
| 1 | Módulo e copyright | Declara o AutoGestor, a autoria e os direitos autorais de Marcio Ramos. |
| 26 | `localizar_navegador_windows()` | Localiza navegadores nos caminhos usuais do Windows. |
| 48 | `abrir_link_whatsapp()` | Abre o WhatsApp Web e automatiza o envio da mensagem. |
| 81 | `conectar_banco()` | Inicializa o SQLite e executa as migrações necessárias. |
| 115 | `_criar_tabela_mensalidades()` | Cria a tabela persistente de parcelas e seus campos financeiros. |
| 144 | `_criar_metadata_sistema()` | Registra nome do AutoGestor, autoria, copyright e versão em `sistema_metadata`. |
| 172 | `_migrar_status_mensalidades()` | Migra status legados e campos de acordo/desconto. |
| 219 | `_atualizar_status_vencidos()` | Converte parcelas pendentes vencidas para `Atrasada`. |
| 23 | `STATUS_OFICIAIS` | Define os quatro status globais: Pendente, Atrasada, Paga e Em Acordo. |
| 24 | `STATUS_FILTROS` | Define os quatro status oficiais e a opção Todas para a filtragem completa de parcelas. |
| 235 | `_avancar_mes()` | Avança um par ano/mês para a geração de mensalidades. |
| 242 | `_sincronizar_mensalidades_cliente()` | Gera parcelas sem alterar pagamentos existentes. |
| 283 | `_sincronizar_mensalidades_existentes()` | Migra dados legados de clientes para mensalidades. |
| 307 | `listar_mensalidades_abertas()` | Lista parcelas pendentes/atrasadas fora de acordos. |
| 326 | `listar_clientes_filtro()` | Retorna clientes para o seletor da aba Parcelas. |
| 336 | `inserir_parcela()` | Insere por `INSERT` a referência `MM/AAAA`, o valor e a data recebidos pela interface. |
| 379 | `listar_parcelas()` | Lista parcelas por cliente nos filtros Todas, Pendente, Atrasada, Paga ou Em Acordo. |
| 411 | `atualizar_status_mensalidade()` | Converte o rótulo Paga para o status interno Pago, altera a parcela e sincroniza o cliente. |
| 469 | `dar_baixa_mensalidades()` | Baixa parcelas, desconto e pagamentos adiantados. |
| 546 | `_normalizar_desconto()` | Valida o desconto informado. |
| 557 | `_normalizar_dias_regua()` | Valida os intervalos da régua de cobrança. |
| 572 | `registrar_acordo()` | Registra nova data/valor e congela alertas antigos. |
| 620 | `_criar_tabela_configuracoes()` | Cria configurações e parâmetros da régua. |
| 665 | `salvar_configuracoes()` | Persiste empresa, PIX, banco e intervalos de cobrança. |
| 711 | `limpar_configuracoes()` | Remove os dados configuráveis da empresa. |
| 725 | `obter_configuracoes()` | Retorna configurações e valores padrão da régua. |
| 753 | `_adicionar_colunas_antigas()` | Atualiza bancos legados de clientes. |
| 782 | `_data_vencimento_do_dia()` | Converte o dia mensal em uma data válida. |
| 791 | `_ler_data_vencimento()` | Lê o vencimento no modo terminal. |
| 804 | `_normalizar_nome()` | Valida e normaliza o nome do cliente. |
| 811 | `_normalizar_telefone()` | Normaliza telefone para o WhatsApp. |
| 822 | `_normalizar_valor()` | Valida valores monetários positivos. |
| 835 | `_normalizar_data_vencimento()` | Aceita dia ou data completa de vencimento. |
| 847 | `_ler_datas_atrasadas()` | Converte datas históricas informadas. |
| 866 | `cadastrar_cliente()` | Cadastra cliente e cria parcelas iniciais. |
| 964 | `atualizar_cliente()` | Atualiza dados cadastrais e parcelas abertas. |
| 1062 | `listar_clientes()` | Lista clientes e status geral atualizado. |
| 1110 | `registrar_pagamento()` | Mantém compatibilidade do fluxo terminal. |
| 1139 | `_telefone_whatsapp()` | Prepara telefone para a URL do WhatsApp. |
| 1144 | `_meses_pendentes()` | Gera referências mensais em aberto. |
| 1167 | `gerar_cobrancas()` | Filtra cobranças pela régua e ignora acordos. |
| 1338 | `excluir_cliente()` | Exclui cliente e histórico de mensalidades. |
| 1367 | `excluir_clientes()` | Remove vários clientes e suas mensalidades associadas em uma transação SQLite. |
| 1399 | `menu()` | Executa o fluxo de operação no terminal. |
