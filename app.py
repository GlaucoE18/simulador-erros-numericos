# -*- coding: utf-8 -*-
"""
=====================================================================
 CALCULADORA DE ERROS - DASHBOARD (interface web do simulador)
=====================================================================

Este arquivo é SÓ a interface. Toda a matemática está em simulador.py,
importado logo abaixo. Assim o terminal e o dashboard usam exatamente as
mesmas funções e, portanto, dão exatamente os mesmos resultados.

Como rodar:
    streamlit run app.py

Como o Streamlit funciona (resumo para a apresentação):
    - O script inteiro roda de cima para baixo a cada interação do usuário
      (digitou um número, clicou num botão -> roda de novo).
    - Cada st.alguma_coisa(...) desenha um elemento na tela.
    - Campos como st.text_input(...) devolvem o valor que está digitado.
    - st.session_state guarda valores entre uma execução e outra (usamos
      para o botão "Limpar / novo cálculo").

Mapa do arquivo
---------------
    1. Configuração da página e estilo
    2. Funções auxiliares de exibição (cards, tabelas, passo a passo)
    3. Barra lateral: configuração da "máquina"
    4. Abas: Calculadora | Exemplos do roteiro | Somas sucessivas |
             Testes extras | Teoria
"""

from decimal import Decimal

import pandas as pd
import streamlit as st

import simulador as sim


# =====================================================================
# 1. CONFIGURAÇÃO DA PÁGINA E ESTILO
# =====================================================================

st.set_page_config(page_title="Calculadora de Erros", page_icon="🧮", layout="wide")

# Cores herdadas do protótipo em Tkinter (fundo escuro, verde-menta e amarelo).
# O CSS abaixo desenha os "cards" de resultado com fonte de código (monoespaçada).
st.markdown("""
<style>
.card {background:#0d1526; border:1px solid #283650; border-radius:10px;
       padding:12px 14px; margin-bottom:10px;}
.card .titulo {color:#8b98b4; font-size:0.72rem; font-weight:700; letter-spacing:.06em;}
.card .valor  {font-family:Consolas, 'Courier New', monospace; font-size:1.15rem;
               font-weight:700; word-break:break-all;}
.card .extra  {color:#8b98b4; font-family:Consolas, monospace; font-size:0.78rem;}
</style>
""", unsafe_allow_html=True)

MENTA, AMARELO, TEXTO, VERMELHO = "#72e3c2", "#ffca78", "#e8edf7", "#ff8a8a"

NOMES_OPERACAO = {"+": "+  Soma", "-": "−  Subtração", "*": "×  Multiplicação", "/": "÷  Divisão"}
NOMES_MODO = {sim.SIGNIFICATIVOS: "Dígitos significativos (roteiro)",
              sim.CASAS: "Casas decimais (como no Ex. 3 do PDF)"}


# =====================================================================
# 2. FUNÇÕES AUXILIARES DE EXIBIÇÃO
# =====================================================================

def card(titulo, valor, cor=TEXTO, extra=""):
    """Desenha um card com título pequeno e valor grande (estilo do protótipo)."""
    st.markdown(f"<div class='card'><div class='titulo'>{titulo}</div>"
                f"<div class='valor' style='color:{cor}'>{valor}</div>"
                f"<div class='extra'>{extra}</div></div>", unsafe_allow_html=True)


def cards_resultado(r):
    """Os 5 resultados que o roteiro pede para cada operação."""
    n_mantissa = r["n"] if r["modo"] == sim.SIGNIFICATIVOS else None
    erros = r["erros"]
    colunas = st.columns(5)
    with colunas[0]:
        card("VALOR EXATO", sim.formatar(r["exato"]), TEXTO, sim.formatar_cientifico(r["exato"]))
    with colunas[1]:
        card("VALOR APROXIMADO", sim.formatar_maquina(r["aproximado"]), MENTA,
             sim.formatar_cientifico(r["aproximado"], n_mantissa))
    with colunas[2]:
        card("ERRO ABSOLUTO (Ea)", sim.formatar_erro(erros["absoluto"]), AMARELO, "|exato − aprox|")
    with colunas[3]:
        card("ERRO RELATIVO (Er)", sim.formatar_erro(erros["relativo"]),
             AMARELO if erros["relativo"] is not None else VERMELHO, "Ea / |aprox|")
    with colunas[4]:
        card("ERRO RELATIVO (%)", sim.formatar_percentual(erros["percentual"]),
             AMARELO if erros["relativo"] is not None else VERMELHO, "Er × 100")


def avisos(r):
    """Mensagens que ajudam a interpretar o resultado."""
    if r["aproximado"] == 0 and r["exato"] != 0:
        st.error("**Subtração nula!** Na máquina, o resultado virou 0. Perdemos 100% da informação "
                 "e o erro relativo nem pode ser calculado (divisão por zero).")
    elif r["op"] == "-" and r["exato"] != 0 and r["erros"]["relativo"] is not None \
            and r["erros"]["relativo"] > Decimal("0.01"):
        st.warning("**Cancelamento subtrativo:** x e y são muito próximos, os dígitos iguais se "
                   "cancelaram e o erro relativo ficou grande.")
    if Decimal(repr(r["resultado_float"])) != r["exato"]:
        st.caption(f"Curiosidade: com float (double) do Python, essa conta dá "
                   f"`{r['resultado_float']!r}`. O próprio float tem erro de representação, "
                   f"por isso o simulador usa `Decimal`.")


def passo_a_passo(r):
    """Explica a conta em etapas, do jeito que fazemos no caderno."""
    simbolo = sim.OPERACOES[r["op"]]
    n, modo, metodo = r["n"], r["modo"], r["metodo"]
    n_mantissa = n if modo == sim.SIGNIFICATIVOS else None
    erros = r["erros"]
    linhas = [
        f"**1. Valor exato:** `{sim.formatar(r['x'])} {simbolo} {sim.formatar(r['y'])} = "
        f"{sim.formatar(r['exato'])}` → normalizado `{sim.formatar_cientifico(r['exato'])}`",
    ]
    if r["ajustar_operandos"]:
        linhas.append(
            f"**2. Operandos guardados com {sim.descrever_precisao(n, modo)}:** "
            f"x = `{sim.formatar_maquina(r['x_maquina'])}` "
            f"(`{sim.formatar_cientifico(r['x_maquina'], n_mantissa)}`), "
            f"y = `{sim.formatar_maquina(r['y_maquina'])}` "
            f"(`{sim.formatar_cientifico(r['y_maquina'], n_mantissa)}`)")
    else:
        linhas.append("**2. Operandos:** usados sem ajuste (opção desligada na barra lateral)")
    linhas += [
        f"**3. Conta da máquina:** `{sim.formatar_maquina(r['x_maquina'])} {simbolo} "
        f"{sim.formatar_maquina(r['y_maquina'])} = {sim.formatar(r['resultado_bruto'])}`",
        f"**4. Corte em {sim.descrever_precisao(n, modo)}:** "
        f"`{sim.formatar_corte(r['resultado_bruto'], n, modo)}` → {metodo} → "
        f"`{sim.formatar_maquina(r['aproximado'])}`",
        f"**5. Erros:** Ea = |{sim.formatar(r['exato'])} − {sim.formatar_maquina(r['aproximado'])}| = "
        f"`{sim.formatar_erro(erros['absoluto'])}`;  Er = Ea / |aprox| = "
        f"`{sim.formatar_erro(erros['relativo'])}`",
    ]
    st.markdown("\n\n".join(linhas))


def tabela_comparacao(resultados):
    """Truncamento × arredondamento lado a lado, para as mesmas entradas."""
    return pd.DataFrame([{
        "Método": metodo.capitalize(),
        "x na máquina": sim.formatar_maquina(r["x_maquina"]),
        "y na máquina": sim.formatar_maquina(r["y_maquina"]),
        "Exato": sim.formatar(r["exato"]),
        "Aproximado": sim.formatar_maquina(r["aproximado"]),
        "Erro absoluto": sim.formatar_erro(r["erros"]["absoluto"]),
        "Erro relativo": sim.formatar_erro(r["erros"]["relativo"]),
        "Er (%)": sim.formatar_percentual(r["erros"]["percentual"]),
    } for metodo, r in resultados.items()])


def tabela_passos(resultado):
    """Cada soma do Exemplo 3 / somas sucessivas, uma linha por passo."""
    return pd.DataFrame([{
        "Soma": p["passo"],
        "Conta": f"{sim.formatar_maquina(p['anterior'])} + {sim.formatar_maquina(p['parcela'])}",
        "Resultado bruto": sim.formatar(p["soma_bruta"]),
        "Guardado": sim.formatar_maquina(p["armazenado"]),
        "Exato": sim.formatar(p["exato"]),
        "Erro acumulado": sim.formatar_erro(p["erro_absoluto"]),
    } for p in resultado["passos"]])


def grafico_erro(resultados):
    """Gráfico do erro absoluto acumulado a cada soma, para os dois métodos."""
    dados = pd.DataFrame({
        metodo.capitalize(): [float(p["erro_absoluto"]) for p in r["passos"]]
        for metodo, r in resultados.items()
    }, index=[p["passo"] for p in next(iter(resultados.values()))["passos"]])
    dados.index.name = "Soma"
    st.line_chart(dados, x_label="Número da soma", y_label="Erro absoluto acumulado",
                  color=[AMARELO, MENTA])


def resumo_final(resultado):
    """Linha de cards com o resultado final das somas sucessivas."""
    erros = resultado["erros"]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("EXATO", sim.formatar(resultado["exato"]))
    with c2:
        card("APROXIMADO", sim.formatar_maquina(resultado["aproximado"]), MENTA)
    with c3:
        card("Ea TOTAL", sim.formatar_erro(erros["absoluto"]), AMARELO)
    with c4:
        card("Er TOTAL", sim.formatar_percentual(erros["percentual"]), AMARELO)


# =====================================================================
# 3. BARRA LATERAL: CONFIGURAÇÃO DA "MÁQUINA"
# =====================================================================

# Valores iniciais (usados na primeira vez e pelo botão "Limpar").
PADROES = {"x": "0.76545", "y": "0.76541", "op": "-", "n": 4,
           "metodo": sim.ARREDONDAMENTO, "modo": sim.SIGNIFICATIVOS, "ajustar_operandos": True}
for chave, valor in PADROES.items():
    st.session_state.setdefault(chave, valor)


def limpar():
    """Botão 'Limpar / novo cálculo': esvazia x e y e volta ao padrão t = 4."""
    for chave, valor in PADROES.items():
        st.session_state[chave] = valor
    st.session_state["x"], st.session_state["y"], st.session_state["op"] = "", "", "+"


with st.sidebar:
    st.markdown(f"<h2 style='color:{MENTA};margin-bottom:0'>Calculadora de Erros</h2>", unsafe_allow_html=True)
    st.caption("SIMULADOR DE PROPAGAÇÃO DE ERROS NUMÉRICOS")
    st.subheader("⚙️ Máquina hipotética")
    modo = st.radio("Como contar os n dígitos", sim.MODOS, format_func=NOMES_MODO.get, key="modo")
    n = int(st.number_input("n (o roteiro usa t = 4)", sim.N_MIN, sim.N_MAX, step=1, key="n"))
    metodo = st.radio("Método de ajuste", sim.METODOS, format_func=str.capitalize, key="metodo")
    ajustar_operandos = st.toggle("Guardar x e y também com n dígitos", key="ajustar_operandos",
                                  help="É o que o Exemplo 2 pede: 'armazenar x e y com 4 dígitos' "
                                       "antes de fazer a conta.")
    st.button("🧹 Limpar / novo cálculo", on_click=limpar, width="stretch")
    st.divider()
    st.caption("Cálculo Numérico · UNIVASF · 2026.2\n\nProjeto Unidade 1 (Erros)")


# =====================================================================
# 4. ABAS
# =====================================================================

st.title("🧮 Simulador de Propagação de Erros Numéricos")
st.caption(f"Máquina atual: **{sim.descrever_precisao(n, modo)}**, com **{metodo}**. "
           "Mude a configuração na barra lateral.")

aba_calc, aba_ex, aba_somas, aba_extras, aba_teoria = st.tabs(
    ["🧮 Calculadora", "📋 Exemplos do roteiro", "🔁 Somas sucessivas", "🧪 Testes extras", "📖 Teoria"])


# ---------------------------------------------------------------- Calculadora
with aba_calc:
    c_x, c_op, c_y = st.columns([3, 2, 3])
    x_texto = c_x.text_input("Valor de x", key="x", placeholder="ex.: 0,76545")
    op = c_op.selectbox("Operação", list(sim.OPERACOES), format_func=NOMES_OPERACAO.get, key="op")
    y_texto = c_y.text_input("Valor de y", key="y", placeholder="ex.: 0,76541")

    if not x_texto.strip() or not y_texto.strip():
        st.info("Digite x e y para calcular (aceita vírgula ou ponto, e notação como 4e-5).")
    else:
        try:
            r = sim.simular_operacao(x_texto, y_texto, op, n, metodo, modo, ajustar_operandos)
            comparacao = sim.comparar_metodos(x_texto, y_texto, op, n, modo, ajustar_operandos)
        except (ValueError, ZeroDivisionError) as erro:
            st.error(f"Não foi possível calcular: {erro}")
        else:
            cards_resultado(r)
            avisos(r)
            st.subheader("Passo a passo")
            passo_a_passo(r)
            st.subheader("Truncamento × arredondamento")
            st.dataframe(tabela_comparacao(comparacao), hide_index=True)
            st.caption("Mesmas entradas e mesmo n; só muda o método de ajuste.")


# ---------------------------------------------------------- Exemplos do roteiro
with aba_ex:
    st.markdown(f"Todos os exemplos usam a máquina da barra lateral (**{sim.descrever_precisao(n, modo)}**) "
                "e mostram **os dois métodos** lado a lado, como pede o roteiro.")

    # Exemplo 1 -------------------------------------------------------------
    st.header("Exemplo 1: Operação simples (soma)")
    st.markdown("Somar dois números com 5 casas decimais. A equipe escolheu **π ≈ 3.14159** e "
                "**e ≈ 2.71828**, mas dá para trocar.")
    c1, c2 = st.columns(2)
    ex1_x = c1.text_input("x (5 casas decimais)", str(sim.EX1_X), key="ex1_x")
    ex1_y = c2.text_input("y (5 casas decimais)", str(sim.EX1_Y), key="ex1_y")
    try:
        st.dataframe(tabela_comparacao(sim.exemplo_1(n, modo, sim.ler_numero(ex1_x), sim.ler_numero(ex1_y))),
                     hide_index=True)
    except ValueError as erro:
        st.error(str(erro))
    st.markdown("**O que observar:** o truncamento sempre leva o valor para baixo (em módulo); o "
                "arredondamento escolhe o valor guardável mais próximo, então o erro dele fica, no "
                "máximo, em meia unidade do último dígito.")

    # Exemplo 2 -------------------------------------------------------------
    st.header("Exemplo 2: Cancelamento subtrativo")
    st.markdown("x = **0.76545** e y = **0.76541** (diferem só na última casa). Valor exato: "
                "0.76545 − 0.76541 = **0.00004** = 0.4 × 10⁻⁴.")
    resultados_ex2 = sim.exemplo_2(n, modo)
    st.dataframe(tabela_comparacao(resultados_ex2), hide_index=True)
    for r2 in resultados_ex2.values():
        with st.expander(f"Passo a passo com {r2['metodo']}"):
            passo_a_passo(r2)
            avisos(r2)
    st.markdown("**O que observar:** x e y estavam corretos em 4 dígitos, mas são quase iguais. Na "
                "subtração, os dígitos iguais se cancelam e sobra só o último, que era justamente o "
                "que tinha erro. Com arredondamento o erro relativo chega a **60%**; com "
                "truncamento a resposta vira **0** (subtração nula).")

    # Exemplo 3 -------------------------------------------------------------
    st.header("Exemplo 3: Propagação do erro em uma sequência de somas")
    st.markdown("Somar **0.56786** dez vezes. Exato: 10 × 0.56786 = **5.6786**. Depois de cada "
                "soma, a máquina guarda só n dígitos, e o erro de um passo entra no passo seguinte.")
    if modo == sim.SIGNIFICATIVOS:
        st.info("**Atenção ao PDF:** o roteiro mostra 1.1357, 1.7035, 2.2713… Esses valores têm "
                "4 **casas decimais** (5 dígitos significativos). Com 4 dígitos significativos de "
                "verdade, o resultado é 1.135, 1.702, 2.269… Para reproduzir exatamente o PDF, "
                "mude *Como contar os n dígitos* para **Casas decimais** na barra lateral.")
    resultados_ex3 = sim.exemplo_3(n, modo)
    for metodo_ex3, r3 in resultados_ex3.items():
        st.subheader(metodo_ex3.capitalize())
        resumo_final(r3)
        st.dataframe(tabela_passos(r3), hide_index=True)
    st.subheader("Como o erro cresce a cada soma")
    grafico_erro(resultados_ex3)
    st.markdown("**O que observar:** o erro de cada soma entra na soma seguinte (propagação). "
                "Com 4 dígitos significativos, o truncamento perde **~0.00086 por soma**, sempre "
                "para baixo, e o erro cresce em linha reta. O arredondamento erra só **~0.00014 por "
                "soma** (aqui sempre para cima, porque a parcela é sempre a mesma). Os dois "
                "acumulam, mas o arredondamento erra cerca de 6× menos.")


# ------------------------------------------------------------ Somas sucessivas
with aba_somas:
    st.markdown("Generalização do Exemplo 3: escolha a parcela, quantas vezes somar e, se quiser, "
                "um valor inicial.")
    c1, c2, c3 = st.columns(3)
    parcela_txt = c1.text_input("Parcela (valor somado)", "0.56786", key="parcela")
    vezes = int(c2.number_input("Quantidade de parcelas", 1, 10_000, 10, step=1, key="vezes"))
    inicial_txt = c3.text_input("Valor inicial (opcional)", "", key="inicial",
                                help="Vazio: começa com a 1ª parcela, como no roteiro. "
                                     "Preenchido: começa desse valor e soma a parcela N vezes.")
    ajustar_parcela = st.toggle("Guardar a parcela também com n dígitos", value=False, key="ajustar_parcela",
                                help="O PDF usa 0.56786 inteiro em cada soma, por isso vem desligado.")
    try:
        resultados_somas = {
            m: sim.simular_somas_sucessivas(parcela_txt, vezes, n, m, modo,
                                            inicial=inicial_txt or None, ajustar_parcela=ajustar_parcela)
            for m in sim.METODOS}
    except ValueError as erro:
        st.error(str(erro))
    else:
        for metodo_s, rs in resultados_somas.items():
            st.subheader(metodo_s.capitalize())
            resumo_final(rs)
        if any(r["passos"] for r in resultados_somas.values()):
            grafico_erro(resultados_somas)
            for metodo_s, rs in resultados_somas.items():
                with st.expander(f"Tabela passo a passo: {metodo_s}"):
                    st.dataframe(tabela_passos(rs), hide_index=True)


# ---------------------------------------------------------------- Testes extras
with aba_extras:
    st.markdown("Testes criados pela equipe além dos três do roteiro.")

    st.header("A) Divisão com dízima: 2 ÷ 3")
    st.dataframe(tabela_comparacao(sim.teste_divisao(n, modo)), hide_index=True)
    st.markdown("0.666… não cabe em nenhuma máquina finita. Truncando, o último dígito fica 6; "
                "arredondando, vira 7, e o erro cai pela metade.")

    st.header("B) A ordem das somas importa")
    t = sim.teste_ordem_das_somas(n, metodo)
    c1, c2, c3 = st.columns(3)
    with c1:
        card("EXATO: 1000 + 10 × 0.4", sim.formatar(t["exato"]))
    with c2:
        card("1000 PRIMEIRO, DEPOIS 0.4 (10×)", sim.formatar_maquina(t["grande_primeiro"]["aproximado"]), VERMELHO)
    with c3:
        card("0.4 (10×) PRIMEIRO, DEPOIS + 1000", sim.formatar_maquina(t["pequenos_primeiro"]["aproximado"]), MENTA)
    st.markdown("Com 4 dígitos, 1000 + 0.4 = 1000.4 **não cabe** e volta a ser 1000: a parcela "
                "pequena \"some\" em todos os passos. Somando os pequenos primeiro (0.4 × 10 = 4.0), "
                "eles ganham tamanho antes de encontrar o 1000. Na matemática a soma é associativa; "
                "na máquina de precisão finita, **não é**.")

    st.header("C) Exemplo 3 com 100 somas")
    muitas = sim.teste_muitas_somas(100, n, modo)
    for metodo_c, rc in muitas.items():
        st.subheader(metodo_c.capitalize())
        resumo_final(rc)
    grafico_erro(muitas)
    st.markdown("Repare no \"joelho\" do gráfico perto da **17ª soma**: é quando o acumulado passa "
                "de 10. Com 4 dígitos significativos, um número entre 1 e 10 tem 3 casas decimais "
                "(5.671), mas um número entre 10 e 100 tem só 2 (10.21). A partir daí, cada soma "
                "perde 10× mais. No ponto flutuante, o erro **absoluto** depende do tamanho do "
                "número; o que se mantém é o erro **relativo**.")

    st.header("D) O próprio float também erra")
    st.dataframe(pd.DataFrame([{"Conta": conta, "Resultado com float": repr(f),
                                "Resultado com Decimal": sim.formatar(d)}
                               for conta, f, d in sim.curiosidades_float()]), hide_index=True)
    st.markdown("O float guarda os números em **base 2**, e 0.1, 0.29 e 0.76545 não têm "
                "representação finita em base 2. Por isso o simulador usa `Decimal` (base 10) para o "
                "valor exato e para o truncamento/arredondamento.")


# ------------------------------------------------------------------------ Teoria
with aba_teoria:
    st.header("Ponto flutuante normalizado")
    st.markdown("Uma máquina com base β = 10 e **t** dígitos guarda todo número ≠ 0 na forma:")
    st.latex(r"x = \pm\, 0.d_1 d_2 \dots d_t \times 10^{e}, \qquad d_1 \neq 0")
    st.markdown("Exemplo do roteiro: 123.45 = 0.12345 × 10³. Se o número tiver mais de t dígitos, a "
                "máquina precisa se livrar do excesso.")

    st.header("Truncamento × arredondamento")
    st.markdown("""
| | Regra | 1.13572 com t = 4 | Erro máximo |
|---|---|---|---|
| **Truncamento** | descarta os dígitos que sobram | 0.1135 × 10¹ = 1.135 | 1 unidade do último dígito |
| **Arredondamento** | se o 1º descartado ≥ 5, soma 1 | 0.1136 × 10¹ = 1.136 | ½ unidade do último dígito |
""")

    st.header("Erros")
    st.latex(r"E_a = |\,x_{exato} - x_{aprox}\,| \qquad\qquad E_r = \frac{E_a}{|\,x_{aprox}\,|}")
    st.markdown("O roteiro divide pelo **aproximado**. Quando o aproximado é 0 (subtração nula), "
                "Er não existe.")

    st.header("Os dois vilões")
    st.markdown("""
- **Cancelamento subtrativo:** subtrair números muito próximos elimina os dígitos iguais e sobra só
  o "lixo" do final. O erro absoluto é pequeno, mas o **relativo** explode (Exemplo 2: 60%).
- **Propagação/acumulação:** em contas em sequência, o erro de cada passo vira dado de entrada do
  passo seguinte. Com truncamento o viés é sempre para o mesmo lado e o erro cresce sem parar
  (Exemplo 3).
""")

st.divider()
st.caption("Calculadora de Erros · Cálculo Numérico · UNIVASF · 2026.2 · Código-fonte: simulador.py (matemática) "
           "+ app.py (interface)")
