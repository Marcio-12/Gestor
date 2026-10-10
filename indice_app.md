# Índice de `app.py`

| Número da Linha | Componente / Aba / Função / Evento | Descrição resumida |
| --- | --- | --- |
| 1 | Módulo e copyright | Importa a interface, SQLite e identifica a autoria do software. |
| 16 | `formatar_valor_moeda()` | Aplica máscara de reais aos campos monetários. |
| 30 | `AppGestor(ctk.CTk)` | Classe principal da interface gráfica. |
| 32 | `__init__()` | Monta janela, formulários, abas, tabelas, filtros e rodapé. |
| 255 | `abas_financeiras` | Cria as abas principais `Clientes` e `Parcelas`. |
| 258 | Aba `Parcelas` | Centraliza a gestão financeira individual por cliente. |
| 342 | `frame_inserir_parcela` | Exibe logo abaixo do menu os campos de data, valor e o botão azul de inserção; a referência é gerada a partir do mês da data. |
| 354 | Eventos de máscara | Conecta `KeyRelease` aos campos de data e valor. |
| 403 | `tree_parcelas` | Tabela de parcelas com cliente, referência, vencimento, valor e status. |
| 448 | `atualizar_tabela()` | Recarrega a tabela de clientes. |
| 471 | `atualizar_tabela_parcelas()` | Filtra parcelas pela combinação de cliente e status selecionados: Todas, Pendente, Atrasada, Paga ou Em Acordo. |
| 505 | `carregar_clientes_parcelas()` | Atualiza o menu com clientes cadastrados e seus IDs. |
| 527 | `filtrar_parcelas_por_cliente()` | Exibe parcelas do cliente selecionado, ou de todos os clientes, em conjunto com o status escolhido e controla o botão de inserção. |
| 537 | `inserir_parcela()` | Valida data e valor, gera a referência `MM/AAAA` a partir da data, insere a parcela e atualiza as tabelas. |
| 577 | `_substituir_texto_mascarado()` | Atualiza uma entrada mascarada sem recursão de eventos. |
| 590 | `formatar_data_parcela()` | Formata a data automaticamente como `DD/MM/AAAA` ao digitar. |
| 600 | `formatar_valor_parcela()` | Formata o valor em reais com vírgula e centavos. |
| 614 | `alterar_status_parcela()` | Permite selecionar exatamente Pendente, Atrasada, Paga ou Em Acordo e persiste a alteração no SQLite. |
| 655 | `carregar_configuracoes()` | Carrega configurações persistidas nos campos da aba. |
| 676 | `salvar_configuracoes()` | Salva empresa e régua com tratamento visual de erros. |
| 692 | `limpar_configuracoes()` | Confirma e limpa configurações da empresa. |
| 716 | `formatar_valor_digitado()` | Formata valores enquanto o usuário digita. |
| 725 | `formatar_datas_digitadas()` | Mantido para compatibilidade com entradas históricas legadas. |
| 761 | `verificar_formulario_limpo()` | Cancela edição quando o formulário é limpo. |
| 773 | `cadastrar_cliente()` | Valida campos base e cadastra ou atualiza um cliente. |
| 812 | `editar_cliente()` | Carrega dados base do cliente para edição. |
| 835 | `_dia_do_valor()` | Extrai o dia exibido na tabela. |
| 841 | `cancelar_edicao()` | Limpa o formulário e restaura o modo de cadastro. |
| 853 | `marcar_como_pago()` | Fluxo legado de baixa mantido apenas para compatibilidade. |
| 948 | `registrar_acordo()` | Fluxo legado de acordo mantido apenas para compatibilidade. |
| 982 | `excluir_cliente()` | Exclui o cliente selecionado após confirmação. |
| 1004 | `disparar_cobrancas()` | Valida configurações e inicia a thread de cobrança. |
| 1029 | `_executar_cobrancas_em_background()` | Executa o backend sem bloquear a interface. |
| 1041 | `_finalizar_cobrancas()` | Reabilita o botão e apresenta o resultado ao usuário. |
