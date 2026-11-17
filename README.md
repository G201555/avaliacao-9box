# Avaliação 9-box

Sistema de avaliação mensal de consultores de campo na matriz 9-box (desempenho × potencial), com o ciclo calculado direto do banco.

## Como funciona

- **Cálculo do ciclo** (`gerar_ciclo.py`): pontuação de desempenho a partir das métricas de execução no SQL Server, com a mesma mecânica da campanha de incentivo, e efetividade pela query do relatório oficial (`sql/`).
- **Conferência** (`conferir_pbi.py`): compara o cálculo com o relatório de Power BI para garantir que os números batem.
- **Publicação** (`publicar_ciclos.js`, `importar.py`): grava o ciclo no Firestore; o admin também pode importar pelo botão no site.
- **Acesso por perfil** (`firestore.rules`): admin, supervisor, leitor e o próprio consultor, que vê só a própria avaliação. As regras são testadas com `testar_regras.js`.
- **Mapa por UF** (`gerar_mapa.py`) com a malha do IBGE.

## Stack

Python, pandas, SQL Server, JavaScript, Firebase Auth, Firestore, Hosting.

---
Projeto feito no trabalho, publicado sem dados. Nomes de pessoas foram removidos do código.
