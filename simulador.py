# -*- coding: utf-8 -*-
"""
=====================================================================
 CALCULADORA DE ERROS - SIMULADOR DE PROPAGAÇÃO DE ERROS NUMÉRICOS
 Cálculo Numérico - UNIVASF - Projeto Unidade 1 (Erros) - 2026.2
 Equipe: Glauco Erasmo, Cristiana Campinho e Alexandre Macedo
=====================================================================

Ideia geral
-----------
Um computador guarda os números com uma quantidade FINITA de dígitos.
Este programa imita uma "máquina hipotética" que só consegue guardar
n dígitos significativos (no roteiro do trabalho, t = 4) e mostra o que
acontece com o resultado das contas quando cortamos (TRUNCAMENTO) ou
arredondamos (ARREDONDAMENTO) os dígitos que sobram.

Para cada conta o simulador mostra:
    - o valor exato        -> conta feita com precisão máxima (50 dígitos)
    - o valor aproximado   -> conta feita pela "máquina" de n dígitos
    - o erro absoluto      Ea = |exato - aproximado|
    - o erro relativo      Er = Ea / |aproximado|      (fórmula do roteiro)

Como executar
-------------
    python simulador.py        -> menu interativo no terminal
    index.html (no navegador)  -> calculadora web, que roda ESTE arquivo
                                  dentro do navegador (ver PARTE 9)

Mapa do arquivo (de cima para baixo)
------------------------------------
    PARTE 1 - Configurações gerais
    PARTE 2 - Leitura dos números digitados
    PARTE 3 - Ponto flutuante: normalização, truncamento e arredondamento
    PARTE 4 - Operações aritméticas e cálculo dos erros
    PARTE 5 - Simulações completas (uma operação / somas sucessivas)
    PARTE 6 - Exemplos do roteiro e testes extras da equipe
    PARTE 7 - Formatação dos números para exibir
    PARTE 8 - Menu interativo no terminal
    PARTE 9 - Ponte com a página web (index.html)

Histórico
---------
A primeira versão (protótipo com janela em Tkinter, feito pelo Alexandre Macedo)
usava float. Ao testar, percebemos que o próprio float atrapalhava a
simulação: truncar 0.29 com 2 dígitos dava 0.28, porque o computador
guarda 0.29 como 0.28999999999999998... Por isso esta versão usa o
módulo decimal, que faz as contas em base 10, igual fazemos no caderno.
"""

import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP, getcontext


# =====================================================================
# PARTE 1 - CONFIGURAÇÕES GERAIS
# =====================================================================

# Precisão usada para o "valor exato": 50 dígitos decimais.
# Um float comum (double) guarda só uns 15 a 17 dígitos, então 50 sobra.
# Para +, - e x com números digitados pelo usuário o resultado em Decimal
# é EXATO de verdade. Só na divisão (ex.: 2/3 = 0.666...) existe um corte,
# e ele acontece lá no 50º dígito, longe de qualquer coisa que a gente mede.
getcontext().prec = 50

# Os dois métodos de ajuste pedidos no trabalho.
TRUNCAMENTO = "truncamento"
ARREDONDAMENTO = "arredondamento"
METODOS = (TRUNCAMENTO, ARREDONDAMENTO)

# Como contar os n dígitos:
#   SIGNIFICATIVOS -> n dígitos significativos (é o que o roteiro pede: t = 4)
#   CASAS          -> n casas decimais depois da vírgula (é o que o PDF
#                     acabou usando no Exemplo 3: 1.13572 -> 1.1357)
SIGNIFICATIVOS = "significativos"
CASAS = "casas"
MODOS = (SIGNIFICATIVOS, CASAS)

# Operações: símbolo usado internamente -> símbolo bonito para exibir.
OPERACOES = {"+": "+", "-": "−", "*": "×", "/": "÷"}

# Outras formas que o usuário pode digitar para a mesma operação.
_APELIDOS_OPERACAO = {"x": "*", "X": "*", "×": "*", "÷": "/", ":": "/", "−": "-"}

# Limites de n aceitos pelo simulador.
N_MIN, N_MAX = 1, 15

# Limite de somas na simulação de somas sucessivas (evita travar o programa).
MAX_SOMAS = 100_000


# =====================================================================
# PARTE 2 - LEITURA DOS NÚMEROS DIGITADOS
# =====================================================================

def ler_numero(texto):
    """Converte o que o usuário digitou em um Decimal EXATO.

    - Aceita vírgula ou ponto: "0,76545" e "0.76545" valem a mesma coisa.
    - Aceita notação científica: "4e-5" = 0.00004.
    - NÃO passa por float de propósito: Decimal("0.1") é exatamente 0.1,
      enquanto o float 0.1 vale na verdade 0.1000000000000000055511151...

    Se o texto não for um número, levanta ValueError com uma mensagem
    amigável (o menu e a página web mostram essa mensagem para o usuário).
    """
    if isinstance(texto, Decimal):
        return texto
    if isinstance(texto, (int, float)):
        texto = str(texto)  # str(0.1) = "0.1", que é o que a pessoa quis dizer

    limpo = str(texto).strip().replace(" ", "").replace(",", ".")
    if limpo == "":
        raise ValueError("Campo vazio: digite um número.")
    try:
        valor = Decimal(limpo)
    except InvalidOperation:
        raise ValueError(f"'{texto}' não é um número válido.") from None
    if not valor.is_finite():
        raise ValueError("Use apenas números finitos (sem 'inf' ou 'nan').")
    return valor


def padronizar_operacao(op):
    """Transforma 'x', '×', '÷', ':' etc. em um dos símbolos + - * /."""
    op = str(op).strip()
    op = _APELIDOS_OPERACAO.get(op, op)
    if op not in OPERACOES:
        raise ValueError(f"Operação '{op}' inválida. Use +, -, * ou /.")
    return op


def _validar(n, metodo, modo):
    """Confere se n, método e modo são válidos antes de qualquer conta."""
    if metodo not in METODOS:
        raise ValueError(f"Método '{metodo}' inválido. Use 'truncamento' ou 'arredondamento'.")
    if modo not in MODOS:
        raise ValueError(f"Modo '{modo}' inválido. Use 'significativos' ou 'casas'.")
    if not isinstance(n, int) or not N_MIN <= n <= N_MAX:
        raise ValueError(f"n deve ser um inteiro entre {N_MIN} e {N_MAX}.")


# =====================================================================
# PARTE 3 - PONTO FLUTUANTE: NORMALIZAÇÃO, TRUNCAMENTO E ARREDONDAMENTO
# =====================================================================
#
# Na aula vimos o sistema de ponto flutuante F(β, t, m, M): base β,
# t dígitos na mantissa e expoente entre -m e M. Aqui a base é β = 10
# e t = n (o usuário escolhe). Todo número diferente de zero é escrito
# na forma NORMALIZADA:
#
#         x = ± 0.d1 d2 d3 ... dt × 10^e      com d1 ≠ 0
#
# Exemplo do roteiro:  123.45  =  0.12345 × 10^3
#
# Se o número tiver mais dígitos do que t, a máquina precisa "jogar fora"
# o excesso. Existem duas formas de fazer isso, e o trabalho é comparar
# as duas:
#
#   TRUNCAMENTO    -> descarta os dígitos que sobram, sem olhar para eles.
#   ARREDONDAMENTO -> olha o primeiro dígito descartado: se for >= 5,
#                     soma 1 no último dígito que ficou.
# ---------------------------------------------------------------------

def normalizar(valor, n_digitos=None):
    """Escreve o número na forma normalizada  ± 0.d1d2...dk × 10^e.

    Devolve uma tupla (sinal, digitos, expoente):
        sinal    -> "+" ou "-"
        digitos  -> string com os dígitos da mantissa, ex.: "12345"
        expoente -> o inteiro e

    Se n_digitos for informado, a mantissa é completada com zeros à
    direita até ter esse tamanho (0.586 -> 0.5860), para mostrar quantos
    dígitos a máquina está guardando.

    O zero não tem forma normalizada (não existe d1 ≠ 0), então para ele
    devolvemos ("+", "0", 0).

    Como funciona: valor.adjusted() é a potência de 10 do primeiro dígito
    do número (para 123.45 é 2, porque 1 está na casa das centenas = 10^2).
    Na forma 0.d1d2... o expoente é uma unidade maior: e = adjusted() + 1.
    """
    if valor == 0:
        return "+", "0", 0

    sinal = "-" if valor < 0 else "+"
    digitos = "".join(str(d) for d in valor.as_tuple().digits).rstrip("0") or "0"
    if n_digitos is not None:
        digitos = digitos.ljust(n_digitos, "0")
    expoente = valor.adjusted() + 1
    return sinal, digitos, expoente


def ajustar(valor, n, metodo, modo=SIGNIFICATIVOS):
    """Guarda o valor do jeito que a máquina hipotética guardaria.

    Passo a passo no modo "significativos" (o do roteiro), com n = 4:

        1. Normaliza:          1.13572  =  0.113572 × 10^1
        2. Separa n dígitos:   0.1135 | 72   (o "| 72" não cabe na máquina)
        3. Decide o que fazer com o que sobrou:
             truncamento    -> descarta:                   0.1135 × 10^1
             arredondamento -> o 1º descartado é 7 (>= 5),
                               então soma 1 no último:     0.1136 × 10^1
        4. Volta para a forma decimal: 1.135 (trunc.) ou 1.136 (arred.)

    No modo "casas", n é o número de CASAS DECIMAIS (depois da vírgula).
    Foi o que o PDF usou no Exemplo 3 (1.13572 -> 1.1357, que na verdade
    tem 5 dígitos significativos). Deixamos os dois modos para poder
    reproduzir o PDF e também mostrar o resultado correto com t = 4.

    Implementação: Decimal.quantize() corta o número em uma posição
    decimal exata, seguindo uma regra de arredondamento:
        ROUND_DOWN    = truncamento (corta em direção ao zero, então
                        -1.13572 vira -1.135, como esperado)
        ROUND_HALF_UP = arredondamento "de escola" (5 sobe; para
                        negativos, -0.76545 vira -0.7655)

    Por que não usamos round() do Python? Porque ele faz o "arredondamento
    bancário": quando o descartado é exatamente 5, ele arredonda para o
    dígito PAR. Assim 0.76545 viraria 0.7654, e o roteiro espera 0.7655.
    """
    _validar(n, metodo, modo)
    if valor == 0:
        return Decimal(0)

    regra = ROUND_DOWN if metodo == TRUNCAMENTO else ROUND_HALF_UP

    try:
        if modo == SIGNIFICATIVOS:
            # Potência de 10 do ÚLTIMO dígito que a máquina mantém.
            # Ex.: 1.13572 tem o 1º dígito em 10^0; com n = 4 o último
            # dígito mantido fica em 10^(0 - 3) = 10^-3  ->  1.135
            posicao_ultimo = valor.adjusted() - (n - 1)
            resultado = valor.quantize(Decimal(1).scaleb(posicao_ultimo), rounding=regra)

            # Caso especial do arredondamento: 9.9996 com n = 4 vira 10.000,
            # que tem 5 dígitos (o número "subiu" de 0.9999×10^1 para
            # 0.1000×10^2). Refazemos o ajuste uma casa acima para voltar a
            # ter exatamente n dígitos: 10.00. O valor não muda, só a forma.
            if resultado.adjusted() > valor.adjusted():
                resultado = resultado.quantize(Decimal(1).scaleb(posicao_ultimo + 1), rounding=regra)
        else:
            # Modo casas decimais: o último dígito mantido fica sempre em 10^-n.
            resultado = valor.quantize(Decimal(1).scaleb(-n), rounding=regra)
    except InvalidOperation:
        # Acontece se o número for gigantesco para a precisão de 50 dígitos.
        raise ValueError("Número grande demais para essa configuração de precisão.") from None

    return resultado


# =====================================================================
# PARTE 4 - OPERAÇÕES ARITMÉTICAS E CÁLCULO DOS ERROS
# =====================================================================

def operar(x, y, op):
    """Faz a conta  x op y  com Decimal (precisão de 50 dígitos).

    Aceita op como '+', '-', '*', '/' (ou 'x', '×', '÷').
    Divisão por zero levanta ZeroDivisionError com mensagem em português.
    """
    op = padronizar_operacao(op)
    if op == "+":
        return x + y
    if op == "-":
        return x - y
    if op == "*":
        return x * y
    if y == 0:
        raise ZeroDivisionError("Divisão por zero não é permitida.")
    return x / y


def calcular_erros(exato, aproximado):
    """Calcula os erros entre o valor exato e o valor aproximado.

        Erro absoluto:  Ea = |exato - aproximado|
        Erro relativo:  Er = Ea / |aproximado|       (fórmula do roteiro)
        Percentual:     Er × 100 %

    Quando o aproximado é 0, Er não existe (seria divisão por zero). É o
    que acontece no Exemplo 2 com truncamento: a máquina responde 0 para
    x - y (a "subtração nula"). Nesse caso devolvemos None e a interface
    mostra "indefinido".

    Observação: muitos livros dividem por |exato| em vez de |aproximado|.
    Seguimos o roteiro, mas também devolvemos "relativo_exato" (Ea/|exato|)
    porque ele ajuda a explicar a subtração nula: lá o erro em relação ao
    exato é 100% (perdemos o resultado inteiro).
    """
    absoluto = abs(exato - aproximado)
    relativo = absoluto / abs(aproximado) if aproximado != 0 else None
    relativo_exato = absoluto / abs(exato) if exato != 0 else None
    return {
        "absoluto": absoluto,
        "relativo": relativo,
        "percentual": relativo * 100 if relativo is not None else None,
        "relativo_exato": relativo_exato,
    }


def _operar_float(x, y, op):
    """Mesma conta, mas com float comum (só para curiosidade/comparação)."""
    a, b = float(x), float(y)
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    return a / b


# =====================================================================
# PARTE 5 - SIMULAÇÕES COMPLETAS
# =====================================================================

def simular_operacao(x, y, op, n=4, metodo=ARREDONDAMENTO, modo=SIGNIFICATIVOS,
                     ajustar_operandos=True):
    """Simula UMA operação na máquina de n dígitos e devolve todas as etapas.

    Etapas (as mesmas do roteiro):
        1. Calcula o valor exato com precisão máxima.
        2. Guarda x e y com n dígitos (se ajustar_operandos=True). Isso é o
           que o Exemplo 2 pede: "armazenar x e y com 4 dígitos".
        3. Faz a conta com os operandos da máquina (resultado bruto).
        4. Normaliza e ajusta o resultado para n dígitos (valor aproximado).
        5. Calcula Ea e Er.

    Devolve um dicionário com tudo, para o terminal ou a página web exibirem.
    """
    x, y = ler_numero(x), ler_numero(y)
    op = padronizar_operacao(op)
    _validar(n, metodo, modo)

    exato = operar(x, y, op)                                   # etapa 1

    if ajustar_operandos:                                      # etapa 2
        x_maquina = ajustar(x, n, metodo, modo)
        y_maquina = ajustar(y, n, metodo, modo)
    else:
        x_maquina, y_maquina = x, y

    # Caso raro: no modo casas decimais, um y muito pequeno (ex.: 0.00004 com
    # 4 casas) vira 0 dentro da máquina, e aí a máquina não consegue dividir.
    if op == "/" and y_maquina == 0:
        raise ZeroDivisionError(
            f"y = {formatar(y)} vira 0 quando guardado com {descrever_precisao(n, modo)}, "
            "e a máquina não consegue dividir por zero.")

    resultado_bruto = operar(x_maquina, y_maquina, op)         # etapa 3
    aproximado = ajustar(resultado_bruto, n, metodo, modo)     # etapa 4
    erros = calcular_erros(exato, aproximado)                  # etapa 5

    return {
        "x": x, "y": y, "op": op, "n": n, "metodo": metodo, "modo": modo,
        "ajustar_operandos": ajustar_operandos,
        "exato": exato,
        "x_maquina": x_maquina,
        "y_maquina": y_maquina,
        "resultado_bruto": resultado_bruto,
        "aproximado": aproximado,
        "erros": erros,
        # Curiosidade: a mesma conta feita com float (double). Mostra que a
        # "precisão máxima" do float também tem erro de representação.
        "resultado_float": _operar_float(x, y, op),
    }


def comparar_metodos(x, y, op, n=4, modo=SIGNIFICATIVOS, ajustar_operandos=True):
    """Roda a MESMA operação com truncamento e com arredondamento.

    Devolve {"truncamento": resultado, "arredondamento": resultado}.
    É o que o roteiro pede em todos os testes: "repita usando truncamento
    e arredondamento".
    """
    return {metodo: simular_operacao(x, y, op, n, metodo, modo, ajustar_operandos)
            for metodo in METODOS}


def simular_somas_sucessivas(parcela, quantidade, n=4, metodo=TRUNCAMENTO,
                             modo=SIGNIFICATIVOS, inicial=None, ajustar_parcela=False):
    """Soma a mesma parcela várias vezes, ajustando o acumulado a cada passo.

    É o Exemplo 3 do roteiro ("some 0.56786 dez vezes"). Seguimos o mesmo
    procedimento do PDF:
        Soma 1: 0.56786 + 0.56786 = 1.13572  -> ajusta -> guarda
        Soma 2: (valor guardado) + 0.56786   -> ajusta -> guarda
        ...
    Ou seja, com 10 parcelas são 9 somas, e depois de CADA soma o resultado
    é ajustado para n dígitos. O erro de um passo entra no passo seguinte:
    é isso que chamamos de PROPAGAÇÃO do erro.

    Parâmetros extras:
        inicial         -> se informado, começa a soma a partir desse valor
                           e soma a parcela 'quantidade' vezes (usado no
                           teste "1000 + 0.4 + 0.4 + ...").
        ajustar_parcela -> se True, a própria parcela também é guardada com
                           n dígitos. O PDF usa 0.56786 inteiro em cada
                           soma, por isso o padrão é False.

    Devolve um dicionário com a lista de passos e o resultado final.
    """
    parcela = ler_numero(parcela)
    _validar(n, metodo, modo)
    if not isinstance(quantidade, int) or not 1 <= quantidade <= MAX_SOMAS:
        raise ValueError(f"A quantidade deve ser um inteiro entre 1 e {MAX_SOMAS}.")

    parcela_maquina = ajustar(parcela, n, metodo, modo) if ajustar_parcela else parcela

    if inicial is None:
        # Começa com a 1ª parcela já "na mão" e faz quantidade - 1 somas.
        acumulado = parcela_maquina
        exato = parcela
        numero_de_somas = quantidade - 1
    else:
        # Começa do valor inicial e faz 'quantidade' somas.
        inicial = ler_numero(inicial)
        acumulado = ajustar(inicial, n, metodo, modo)
        exato = inicial
        numero_de_somas = quantidade

    passos = []
    for i in range(1, numero_de_somas + 1):
        anterior = acumulado
        soma_bruta = anterior + parcela_maquina           # conta feita pela máquina
        acumulado = ajustar(soma_bruta, n, metodo, modo)  # máquina guarda só n dígitos
        exato = exato + parcela                           # o que deveria dar
        passos.append({
            "passo": i,
            "anterior": anterior,
            "parcela": parcela_maquina,
            "soma_bruta": soma_bruta,
            "armazenado": acumulado,
            "exato": exato,
            "erro_absoluto": abs(exato - acumulado),
        })

    return {
        "parcela": parcela, "quantidade": quantidade, "n": n,
        "metodo": metodo, "modo": modo, "inicial": inicial,
        "passos": passos,
        "exato": exato,
        "aproximado": acumulado,
        "erros": calcular_erros(exato, acumulado),
    }


# =====================================================================
# PARTE 6 - EXEMPLOS DO ROTEIRO E TESTES EXTRAS DA EQUIPE
# =====================================================================

# Exemplo 1: o roteiro pede "dois números com 5 casas decimais". Escolhemos
# π e e (3.14159 e 2.71828) porque são conhecidos e porque, com 4 dígitos,
# truncamento e arredondamento dão respostas DIFERENTES (5.859 x 5.860).
EX1_X, EX1_Y = Decimal("3.14159"), Decimal("2.71828")

# Exemplo 2: valores do roteiro (diferem só na última casa decimal).
EX2_X, EX2_Y = Decimal("0.76545"), Decimal("0.76541")

# Exemplo 3: valores do roteiro.
EX3_PARCELA, EX3_VEZES = Decimal("0.56786"), 10


def exemplo_1(n=4, modo=SIGNIFICATIVOS, x=EX1_X, y=EX1_Y):
    """Exemplo 1 - soma simples, com truncamento e arredondamento."""
    return comparar_metodos(x, y, "+", n, modo)


def exemplo_2(n=4, modo=SIGNIFICATIVOS, x=EX2_X, y=EX2_Y):
    """Exemplo 2 - cancelamento subtrativo (x e y muito próximos)."""
    return comparar_metodos(x, y, "-", n, modo)


def exemplo_3(n=4, modo=SIGNIFICATIVOS, parcela=EX3_PARCELA, vezes=EX3_VEZES):
    """Exemplo 3 - propagação do erro em uma sequência de somas."""
    return {metodo: simular_somas_sucessivas(parcela, vezes, n, metodo, modo)
            for metodo in METODOS}


def teste_divisao(n=4, modo=SIGNIFICATIVOS):
    """Teste extra A - divisão com dízima: 2 / 3 = 0.6666..."""
    return comparar_metodos("2", "3", "/", n, modo)


def teste_ordem_das_somas(n=4, metodo=ARREDONDAMENTO):
    """Teste extra B - a ORDEM das somas muda o resultado.

    Conta: 1000 + 0.4 + 0.4 + ... (dez vezes 0.4). O exato é 1004.
      Ordem 1 (grande primeiro): 1000 + 0.4 = 1000.4, que com 4 dígitos
              volta a ser 1000. A parcela "some" a cada passo: dá 1000.
      Ordem 2 (pequenos primeiro): 0.4 + 0.4 + ... = 4.0 (cabe em 4
              dígitos), e depois 4.0 + 1000 = 1004. Dá certo!
    Na matemática a soma é associativa; na máquina de n dígitos, não é.
    """
    grande_primeiro = simular_somas_sucessivas("0.4", 10, n, metodo, inicial="1000")
    soma_pequenos = simular_somas_sucessivas("0.4", 10, n, metodo)
    pequenos_primeiro = simular_operacao(soma_pequenos["aproximado"], "1000", "+", n, metodo)
    return {
        "exato": Decimal("1004"),
        "grande_primeiro": grande_primeiro,
        "soma_pequenos": soma_pequenos,
        "pequenos_primeiro": pequenos_primeiro,
    }


def teste_muitas_somas(vezes=100, n=4, modo=SIGNIFICATIVOS):
    """Teste extra C - o Exemplo 3 com muito mais somas (padrão: 100)."""
    return {metodo: simular_somas_sucessivas(EX3_PARCELA, vezes, n, metodo, modo)
            for metodo in METODOS}


def curiosidades_float():
    """Teste extra D - o próprio float (double) também erra.

    O roteiro pede o valor exato "com a precisão máxima da linguagem".
    Estas contas mostram por que preferimos Decimal a float para isso.
    Devolve uma lista de (conta, resultado_em_float, resultado_em_decimal).
    """
    casos = [("0.1", "0.2", "+"), ("0.76545", "0.76541", "-"), ("0.29", "100", "*")]
    return [(f"{x} {OPERACOES[op]} {y}", _operar_float(x, y, op), operar(Decimal(x), Decimal(y), op))
            for x, y, op in casos]


# =====================================================================
# PARTE 7 - FORMATAÇÃO DOS NÚMEROS PARA EXIBIR
# =====================================================================

def formatar(valor, digitos=12, marcar_corte=True, manter_zeros=False):
    """Transforma um Decimal em texto legível.

    - None vira "indefinido" (erro relativo quando o aproximado é 0).
    - Números com mais de 'digitos' dígitos são arredondados só para
      EXIBIR, e ganham "…" no final para avisar que existem mais dígitos
      (ex.: 2/3 = 0.666666666667…). O valor guardado não muda.
    - Zeros à direita sem significado são removidos (5.67860 -> 5.6786),
      a não ser que manter_zeros=True (ver formatar_maquina).
    - Números muito grandes ou muito pequenos aparecem em notação
      científica (ex.: 1.5E-12).
    """
    if valor is None:
        return "indefinido"
    if valor == 0:
        return "0"

    sufixo = ""
    if len(valor.as_tuple().digits) > digitos:
        valor = ajustar(valor, digitos, ARREDONDAMENTO)
        sufixo = "…" if marcar_corte else ""
    if not manter_zeros:
        valor = valor.normalize()

    if -8 <= valor.adjusted() <= 14:
        return format(valor, "f") + sufixo
    return format(valor, "E") + sufixo


def formatar_maquina(valor):
    """Valor guardado pela máquina, MANTENDO os zeros à direita.

    Ex.: com 4 dígitos, 0.7655 - 0.7654 = 0.0001 aparece como 0.0001000,
    ou seja, 0.1000 × 10^-3. Os três zeros finais "ocupam" dígitos da
    mantissa, mas não trazem informação nenhuma: é o retrato do
    cancelamento subtrativo.
    """
    return formatar(valor, manter_zeros=True)


def formatar_erro(valor):
    """Erros são exibidos com 6 dígitos significativos (sem "…")."""
    return formatar(valor, 6, marcar_corte=False)


def formatar_percentual(valor):
    """Erro relativo em porcentagem, ex.: 60 %."""
    return "indefinido" if valor is None else formatar_erro(valor) + " %"


def formatar_cientifico(valor, n_digitos=None):
    """Forma normalizada como texto, ex.: 0.12345 × 10^3."""
    if valor == 0:
        return "0"
    sinal, digitos, expoente = normalizar(valor, n_digitos)
    return f"{'-' if sinal == '-' else ''}0.{digitos} × 10^{expoente}"


def separar_corte(valor, n, modo=SIGNIFICATIVOS):
    """Separa os dígitos que a máquina GUARDA dos que ela DESCARTA.

    Devolve um dicionário com as partes do número:
        sinal        -> "-" ou ""
        inicio       -> "0." no modo significativos; a parte inteira + "."
                        no modo casas decimais
        mantidos     -> os n dígitos que cabem na máquina
        descartados  -> os dígitos que sobram (podem ser "")
        expoente     -> o e de "× 10^e" (None no modo casas decimais)

    Exemplo: 1.13572 com n = 4 (significativos)
        -> inicio "0.", mantidos "1135", descartados "72", expoente 1
        ou seja, 0.1135|72 × 10^1
    """
    if valor == 0:
        return {"sinal": "", "inicio": "", "mantidos": "0", "descartados": "", "expoente": None}
    sinal = "-" if valor < 0 else ""
    if modo == SIGNIFICATIVOS:
        _, digitos, expoente = normalizar(valor)
        return {"sinal": sinal, "inicio": "0.", "mantidos": digitos[:n].ljust(n, "0"),
                "descartados": digitos[n:], "expoente": expoente}
    inteira, _, fracao = format(abs(valor.normalize()), "f").partition(".")
    return {"sinal": sinal, "inicio": inteira + ".", "mantidos": fracao[:n].ljust(n, "0"),
            "descartados": fracao[n:], "expoente": None}


def formatar_corte(valor, n, modo=SIGNIFICATIVOS):
    """Mostra ONDE a máquina corta o número, com uma barra vertical.

        1.13572 com n = 4 (significativos)  ->  0.1135|72 × 10^1
        1.13572 com n = 4 (casas)           ->  1.1357|2

    À esquerda da barra fica o que a máquina guarda; à direita, o que ela
    precisa descartar (truncamento) ou usar para decidir se sobe 1
    (arredondamento).
    """
    if valor == 0:
        return "0"
    c = separar_corte(valor, n, modo)
    texto = f"{c['sinal']}{c['inicio']}{c['mantidos']}|{c['descartados']}"
    if c["expoente"] is not None:
        texto += f" × 10^{c['expoente']}"
    return texto if c["descartados"] else texto + "  (cabe inteiro, nada a descartar)"


def descrever_precisao(n, modo):
    """Texto curto como '4 dígitos significativos' ou '4 casas decimais'."""
    if modo == SIGNIFICATIVOS:
        return f"{n} dígito{'s' if n > 1 else ''} significativo{'s' if n > 1 else ''}"
    return f"{n} casa{'s' if n > 1 else ''} decima{'is' if n > 1 else 'l'}"


# =====================================================================
# PARTE 8 - MENU INTERATIVO NO TERMINAL
# =====================================================================
#
# Tudo daqui para baixo é só "interface": perguntar coisas ao usuário e
# imprimir os resultados. A matemática está toda nas partes 3 a 5.
# ---------------------------------------------------------------------

LINHA = "=" * 72
LINHA_FINA = "-" * 72


def _titulo(texto):
    print("\n" + LINHA)
    print(f"  {texto}")
    print(LINHA)


def _tabela(cabecalho, linhas):
    """Imprime uma tabela simples com colunas alinhadas."""
    larguras = [max(len(str(celula)) for celula in coluna) for coluna in zip(cabecalho, *linhas)]

    def montar(celulas):
        return "  " + " | ".join(str(c).ljust(l) for c, l in zip(celulas, larguras))

    print(montar(cabecalho))
    print("  " + "-+-".join("-" * l for l in larguras))
    for linha in linhas:
        print(montar(linha))


# ---------- Perguntas ao usuário (com validação e valor padrão) ----------

def _perguntar(texto, padrao=None):
    sugestao = f" [{padrao}]" if padrao is not None else ""
    resposta = input(f"  {texto}{sugestao}: ").strip()
    return resposta if resposta else ("" if padrao is None else str(padrao))


def _perguntar_numero(texto, padrao=None):
    while True:
        try:
            return ler_numero(_perguntar(texto, padrao))
        except ValueError as erro:
            print(f"    [!] {erro} Tente de novo (ex.: 0.76545 ou 0,76545).")


def _perguntar_inteiro(texto, minimo, maximo, padrao):
    while True:
        resposta = _perguntar(texto, padrao)
        if resposta.isdigit() and minimo <= int(resposta) <= maximo:
            return int(resposta)
        print(f"    [!] Digite um número inteiro entre {minimo} e {maximo}.")


def _perguntar_sim_nao(texto, padrao=True):
    while True:
        resposta = _perguntar(texto + " (s/n)", "s" if padrao else "n").lower()
        if resposta in ("s", "sim"):
            return True
        if resposta in ("n", "nao", "não"):
            return False
        print("    [!] Responda com s ou n.")


def _perguntar_operacao():
    while True:
        try:
            return padronizar_operacao(_perguntar("Operação (+  -  *  /)", "+"))
        except ValueError as erro:
            print(f"    [!] {erro}")


def _perguntar_metodo():
    while True:
        resposta = _perguntar("Método: (1) truncamento  (2) arredondamento", "2").lower()
        if resposta in ("1", "t", TRUNCAMENTO):
            return TRUNCAMENTO
        if resposta in ("2", "a", ARREDONDAMENTO):
            return ARREDONDAMENTO
        print("    [!] Digite 1 para truncamento ou 2 para arredondamento.")


def _perguntar_modo():
    while True:
        resposta = _perguntar("Contar n como: (1) dígitos significativos  (2) casas decimais", "1")
        if resposta == "1":
            return SIGNIFICATIVOS
        if resposta == "2":
            return CASAS
        print("    [!] Digite 1 ou 2.")


def _pausar():
    input("\n  Pressione Enter para voltar ao menu...")


# ---------- Impressão dos resultados ----------

def imprimir_operacao(r):
    """Mostra uma operação completa, etapa por etapa."""
    simbolo = OPERACOES[r["op"]]
    n, modo = r["n"], r["modo"]
    digitos_mantissa = n if modo == SIGNIFICATIVOS else None

    print(f"\n  Conta: {formatar(r['x'])} {simbolo} {formatar(r['y'])}"
          f"   |   máquina com {descrever_precisao(n, modo)}   |   {r['metodo']}")
    print(LINHA_FINA)
    print(f"  1) Valor exato (precisão máxima) ........ {formatar(r['exato'])}")
    print(f"     forma normalizada .................... {formatar_cientifico(r['exato'])}")
    if r["ajustar_operandos"]:
        print(f"  2) x guardado na máquina ................ {formatar_maquina(r['x_maquina'])}"
              f"   ({formatar_cientifico(r['x_maquina'], digitos_mantissa)})")
        print(f"     y guardado na máquina ................ {formatar_maquina(r['y_maquina'])}"
              f"   ({formatar_cientifico(r['y_maquina'], digitos_mantissa)})")
    else:
        print("  2) x e y usados sem ajuste (opção 'ajustar operandos' desligada)")
    print(f"  3) Conta feita pela máquina ............. {formatar_maquina(r['x_maquina'])} {simbolo} "
          f"{formatar_maquina(r['y_maquina'])} = {formatar(r['resultado_bruto'])}")
    print(f"     onde a máquina corta ................. {formatar_corte(r['resultado_bruto'], n, modo)}")
    print(f"  4) Valor aproximado ({r['metodo']}) ".ljust(42, ".") + f" {formatar_maquina(r['aproximado'])}"
          f"   ({formatar_cientifico(r['aproximado'], digitos_mantissa)})")
    print(f"  5) Erro absoluto  Ea = |exato - aprox| .. {formatar_erro(r['erros']['absoluto'])}")
    if r["erros"]["relativo"] is None:
        print("     Erro relativo  Er = Ea / |aprox| ..... indefinido (o aproximado deu 0!)")
    else:
        print(f"     Erro relativo  Er = Ea / |aprox| ..... {formatar_erro(r['erros']['relativo'])}"
              f"   ({formatar_percentual(r['erros']['percentual'])})")
    print(f"\n  Curiosidade: a mesma conta em float (double) dá {r['resultado_float']!r}")


def imprimir_comparacao(resultados):
    """Tabela lado a lado: truncamento x arredondamento."""
    linhas = []
    for metodo, r in resultados.items():
        linhas.append([
            metodo,
            formatar_maquina(r["x_maquina"]),
            formatar_maquina(r["y_maquina"]),
            formatar_maquina(r["aproximado"]),
            formatar_erro(r["erros"]["absoluto"]),
            formatar_erro(r["erros"]["relativo"]),
            formatar_percentual(r["erros"]["percentual"]),
        ])
    exato = next(iter(resultados.values()))["exato"]
    print(f"\n  Valor exato: {formatar(exato)}")
    _tabela(["Método", "x máquina", "y máquina", "Aproximado", "Ea", "Er", "Er (%)"], linhas)


def imprimir_somas(resultado):
    """Tabela com cada passo das somas sucessivas."""
    print(f"\n  {resultado['metodo'].upper()} - máquina com "
          f"{descrever_precisao(resultado['n'], resultado['modo'])}")
    linhas = [[
        p["passo"],
        f"{formatar_maquina(p['anterior'])} + {formatar_maquina(p['parcela'])}",
        formatar(p["soma_bruta"]),
        formatar_maquina(p["armazenado"]),
        formatar(p["exato"]),
        formatar_erro(p["erro_absoluto"]),
    ] for p in resultado["passos"]]
    _tabela(["Soma", "Conta", "Resultado bruto", "Guardado", "Exato", "Erro acumulado"], linhas)
    erros = resultado["erros"]
    print(f"  Final: exato = {formatar(resultado['exato'])} | aproximado = "
          f"{formatar_maquina(resultado['aproximado'])} | Ea = {formatar_erro(erros['absoluto'])} | "
          f"Er = {formatar_erro(erros['relativo'])} ({formatar_percentual(erros['percentual'])})")


# ---------- Telas de cada exemplo (usadas pelo menu e pelo "rodar tudo") ----------

def mostrar_exemplo_1(x=EX1_X, y=EX1_Y, n=4, modo=SIGNIFICATIVOS):
    _titulo("EXEMPLO 1 - OPERAÇÃO SIMPLES (SOMA)")
    resultados = exemplo_1(n, modo, x, y)
    imprimir_comparacao(resultados)
    print("\n  O que observar: o truncamento sempre joga o valor para BAIXO (em")
    print("  módulo), por isso o erro dele tende a ser maior. O arredondamento")
    print("  escolhe o valor mais próximo, então o erro fica no máximo meia")
    print("  unidade do último dígito guardado.")


def mostrar_exemplo_2(x=EX2_X, y=EX2_Y, n=4, modo=SIGNIFICATIVOS):
    _titulo("EXEMPLO 2 - CANCELAMENTO SUBTRATIVO")
    resultados = exemplo_2(n, modo, x, y)
    imprimir_comparacao(resultados)
    for r in resultados.values():
        if r["aproximado"] == 0:
            print(f"\n  >> Com {r['metodo']}, x e y ficaram IGUAIS na máquina e a subtração")
            print("     deu ZERO (subtração nula): perdemos 100% da informação, e o erro")
            print("     relativo nem pode ser calculado (divisão por zero).")
    print("\n  O que observar: x e y estavam certos em 4 dígitos, mas são quase")
    print("  iguais. Na subtração os dígitos iguais se cancelam e sobra só o")
    print("  último dígito, que era justamente o que tinha erro. Um erro pequeno")
    print("  nos operandos virou um erro relativo enorme no resultado.")


def mostrar_exemplo_3(n=4, modo=SIGNIFICATIVOS, parcela=EX3_PARCELA, vezes=EX3_VEZES):
    _titulo(f"EXEMPLO 3 - PROPAGAÇÃO DO ERRO EM {vezes} SOMAS")
    print(f"  Somar {formatar(parcela)} {vezes} vezes. Exato: {vezes} × {formatar(parcela)} = "
          f"{formatar(parcela * vezes)}")
    for resultado in exemplo_3(n, modo, parcela, vezes).values():
        imprimir_somas(resultado)
    print("\n  O que observar: em cada soma a máquina erra um pedacinho, e esse erro")
    print("  entra na soma seguinte (propagação). No truncamento cada soma perde")
    print("  ~0.00086, sempre para baixo. No arredondamento cada soma erra só")
    print("  ~0.00014 (aqui sempre para cima, porque a parcela é sempre a mesma).")
    print("  Os dois acumulam, mas o arredondamento erra ~6x menos por passo.")


def mostrar_testes_extras(n=4):
    _titulo("TESTE EXTRA A - DIVISÃO COM DÍZIMA (2 / 3)")
    imprimir_comparacao(teste_divisao(n))

    _titulo("TESTE EXTRA B - A ORDEM DAS SOMAS IMPORTA")
    t = teste_ordem_das_somas(n)
    print(f"  Exato: 1000 + 10 × 0.4 = {formatar(t['exato'])}")
    print(f"  Ordem 1 (1000 primeiro, depois 0.4 dez vezes): {formatar_maquina(t['grande_primeiro']['aproximado'])}")
    print(f"  Ordem 2 (soma os 0.4 primeiro = {formatar_maquina(t['soma_pequenos']['aproximado'])}, "
          f"depois + 1000): {formatar_maquina(t['pequenos_primeiro']['aproximado'])}")
    print("  Na ordem 1, 1000.4 não cabe em 4 dígitos e volta a ser 1000 a cada passo.")

    _titulo("TESTE EXTRA C - EXEMPLO 3 COM 100 SOMAS")
    for metodo, r in teste_muitas_somas(100, n).items():
        print(f"  {metodo:<15} aproximado = {formatar_maquina(r['aproximado']):<8} exato = "
              f"{formatar(r['exato'])}   Ea = {formatar_erro(r['erros']['absoluto'])}   "
              f"Er = {formatar_percentual(r['erros']['percentual'])}")

    _titulo("TESTE EXTRA D - O PRÓPRIO FLOAT TAMBÉM ERRA")
    for conta, em_float, em_decimal in curiosidades_float():
        print(f"  {conta:<20} float = {em_float!r:<24} decimal = {formatar(em_decimal)}")


def rodar_todos_os_testes():
    """Roda todos os exemplos do roteiro e os testes extras, sem perguntar nada."""
    mostrar_exemplo_1()
    mostrar_exemplo_2()
    mostrar_exemplo_3()
    _titulo("EXEMPLO 3 COMO NO PDF (4 CASAS DECIMAIS EM VEZ DE 4 DÍGITOS SIGNIFICATIVOS)")
    for resultado in exemplo_3(4, CASAS).values():
        imprimir_somas(resultado)
    mostrar_testes_extras()


# ---------- Opções do menu que fazem perguntas ----------

def _opcao_nova_operacao():
    while True:
        _titulo("NOVA OPERAÇÃO")
        x = _perguntar_numero("Valor de x")
        y = _perguntar_numero("Valor de y")
        op = _perguntar_operacao()
        n = _perguntar_inteiro("Dígitos da máquina (n)", N_MIN, N_MAX, 4)
        metodo = _perguntar_metodo()
        modo = _perguntar_modo()
        ajustar_operandos = _perguntar_sim_nao("Guardar x e y também com n dígitos?", True)
        try:
            imprimir_operacao(simular_operacao(x, y, op, n, metodo, modo, ajustar_operandos))
            print("\n  Comparando os dois métodos:")
            imprimir_comparacao(comparar_metodos(x, y, op, n, modo, ajustar_operandos))
        except (ZeroDivisionError, ValueError) as erro:
            print(f"\n  [!] Não foi possível calcular: {erro}")
        if not _perguntar_sim_nao("\n  Fazer outra operação?", True):
            return


def _opcao_exemplo_1():
    if _perguntar_sim_nao(f"Usar os valores da equipe (x = {EX1_X}, y = {EX1_Y})?", True):
        mostrar_exemplo_1()
    else:
        print("  Digite dois números com 5 casas decimais:")
        mostrar_exemplo_1(_perguntar_numero("x"), _perguntar_numero("y"))
    _pausar()


def _opcao_exemplo_2():
    if _perguntar_sim_nao(f"Usar os valores do roteiro (x = {EX2_X}, y = {EX2_Y})?", True):
        mostrar_exemplo_2()
    else:
        mostrar_exemplo_2(_perguntar_numero("x"), _perguntar_numero("y"))
    _pausar()


def _opcao_exemplo_3():
    mostrar_exemplo_3()
    if _perguntar_sim_nao("\n  Ver também como no PDF (4 casas decimais)?", True):
        _titulo("EXEMPLO 3 COMO NO PDF (4 CASAS DECIMAIS)")
        for resultado in exemplo_3(4, CASAS).values():
            imprimir_somas(resultado)
    _pausar()


def _opcao_somas_personalizadas():
    _titulo("SOMAS SUCESSIVAS PERSONALIZADAS")
    parcela = _perguntar_numero("Valor a ser somado (parcela)", "0.56786")
    vezes = _perguntar_inteiro("Quantas parcelas", 1, MAX_SOMAS, 10)
    n = _perguntar_inteiro("Dígitos da máquina (n)", N_MIN, N_MAX, 4)
    modo = _perguntar_modo()
    for metodo in METODOS:
        resultado = simular_somas_sucessivas(parcela, vezes, n, metodo, modo)
        if len(resultado["passos"]) <= 30:
            imprimir_somas(resultado)
        else:
            # Para muitas somas a tabela ficaria enorme: mostramos só o final.
            erros = resultado["erros"]
            print(f"\n  {metodo.upper()}: aproximado = {formatar_maquina(resultado['aproximado'])} | "
                  f"exato = {formatar(resultado['exato'])} | Ea = {formatar_erro(erros['absoluto'])} | "
                  f"Er = {formatar_percentual(erros['percentual'])}")
    _pausar()


def _opcao_rodar_tudo():
    rodar_todos_os_testes()
    _pausar()


def menu():
    """Laço principal: mostra o menu até o usuário escolher 0 (Sair)."""
    opcoes = {
        "1": ("Nova operação (você escolhe x, y, operação, n e método)", _opcao_nova_operacao),
        "2": ("Exemplo 1 - Soma simples (truncamento x arredondamento)", _opcao_exemplo_1),
        "3": ("Exemplo 2 - Cancelamento subtrativo", _opcao_exemplo_2),
        "4": ("Exemplo 3 - Propagação do erro em 10 somas", _opcao_exemplo_3),
        "5": ("Somas sucessivas personalizadas", _opcao_somas_personalizadas),
        "6": ("Rodar todos os testes do relatório", _opcao_rodar_tudo),
    }
    while True:
        _titulo("Calculadora de Erros - Simulador de Propagação de Erros Numéricos")
        for chave, (descricao, _) in opcoes.items():
            print(f"  {chave}) {descricao}")
        print("  0) Sair")
        escolha = input("\n  Escolha uma opção: ").strip()
        if escolha == "0":
            print("\n  Até a próxima!\n")
            return
        if escolha in opcoes:
            opcoes[escolha][1]()
        else:
            print("  [!] Opção inválida. Digite um número do menu.")


# =====================================================================
# PARTE 9 - PONTE COM A PÁGINA WEB (index.html)
# =====================================================================
#
# A calculadora web roda ESTE arquivo dentro do navegador, com o Pyodide
# (o Python compilado para funcionar em páginas web). O JavaScript da
# página não faz conta nenhuma: ele chama as funções "tela_..." abaixo,
# que usam as mesmas funções das partes 3 a 7, e recebe um texto JSON com
# os números já formatados, prontos para desenhar na tela.
#
# Assim existe uma lógica só: o terminal e a página dão exatamente os
# mesmos resultados.
# ---------------------------------------------------------------------

LIMITE_SOMAS_WEB = 2000   # na página, para a tabela não ficar gigante


def _operacao_para_tela(r):
    """Transforma o dicionário de simular_operacao() em textos para a tela."""
    n, modo = r["n"], r["modo"]
    n_mantissa = n if modo == SIGNIFICATIVOS else None
    erros = r["erros"]
    return {
        "x": formatar(r["x"]), "y": formatar(r["y"]),
        "op": r["op"], "simbolo": OPERACOES[r["op"]],
        "n": n, "metodo": r["metodo"], "modo": modo,
        "precisao": descrever_precisao(n, modo),
        "ajustar_operandos": r["ajustar_operandos"],
        "exato": formatar(r["exato"]),
        "exato_normalizado": formatar_cientifico(r["exato"]),
        "x_maquina": formatar_maquina(r["x_maquina"]),
        "y_maquina": formatar_maquina(r["y_maquina"]),
        "x_corte": separar_corte(r["x"], n, modo),
        "y_corte": separar_corte(r["y"], n, modo),
        "bruto": formatar(r["resultado_bruto"]),
        "bruto_corte": separar_corte(r["resultado_bruto"], n, modo),
        "aproximado": formatar_maquina(r["aproximado"]),
        "aproximado_normalizado": formatar_cientifico(r["aproximado"], n_mantissa),
        "aproximado_zero": r["aproximado"] == 0,
        "exato_zero": r["exato"] == 0,
        "ea": formatar_erro(erros["absoluto"]),
        "er": formatar_erro(erros["relativo"]),
        "er_pct": formatar_percentual(erros["percentual"]),
        "er_indefinido": erros["relativo"] is None,
        "er_alto": erros["relativo"] is not None and erros["relativo"] > Decimal("0.01"),
        "sem_erro": erros["absoluto"] == 0,
        "float": repr(r["resultado_float"]),
        "float_difere": Decimal(repr(r["resultado_float"])) != r["exato"],
    }


def tela_operacao(x, y, op, n, metodo, modo, ajustar_operandos):
    """Chamada pela página quando a pessoa aperta '='.

    Calcula a operação com o método escolhido e também com o outro método
    (para a tabela de comparação). Devolve um JSON com {"ok": True, ...}
    ou {"ok": False, "erro": "mensagem"}.
    """
    try:
        n = int(n)
        r = simular_operacao(x, y, op, n, metodo, modo, bool(ajustar_operandos))
        outro = ARREDONDAMENTO if metodo == TRUNCAMENTO else TRUNCAMENTO
        r_outro = simular_operacao(x, y, op, n, outro, modo, bool(ajustar_operandos))
        return json.dumps({"ok": True, "atual": _operacao_para_tela(r),
                           "outro": _operacao_para_tela(r_outro)})
    except (ValueError, ZeroDivisionError) as erro:
        return json.dumps({"ok": False, "erro": str(erro)})


def _somas_para_tela(r):
    """Transforma o resultado de simular_somas_sucessivas() em textos."""
    erros = r["erros"]
    return {
        "exato": formatar(r["exato"]),
        "aproximado": formatar_maquina(r["aproximado"]),
        "ea": formatar_erro(erros["absoluto"]),
        "er_pct": formatar_percentual(erros["percentual"]),
        "passos": [{
            "passo": p["passo"],
            "conta": f"{formatar_maquina(p['anterior'])} + {formatar_maquina(p['parcela'])}",
            "bruto": formatar(p["soma_bruta"]),
            "guardado": formatar_maquina(p["armazenado"]),
            "exato": formatar(p["exato"]),
            "erro": formatar_erro(p["erro_absoluto"]),
            "erro_numero": float(p["erro_absoluto"]),   # só para desenhar o gráfico
        } for p in r["passos"]],
    }


def tela_somas(parcela, quantidade, n, modo, inicial="", ajustar_parcela=False):
    """Chamada pela aba 'Somas sucessivas': roda os dois métodos."""
    try:
        quantidade = str(quantidade).strip()
        if not quantidade.isdigit() or not 1 <= int(quantidade) <= LIMITE_SOMAS_WEB:
            raise ValueError(f"A quantidade deve ser um inteiro entre 1 e {LIMITE_SOMAS_WEB}.")
        inicial = inicial if str(inicial).strip() else None
        resultado = {metodo: _somas_para_tela(simular_somas_sucessivas(
            parcela, int(quantidade), int(n), metodo, modo, inicial, bool(ajustar_parcela)))
            for metodo in METODOS}
        return json.dumps({"ok": True, **resultado})
    except ValueError as erro:
        return json.dumps({"ok": False, "erro": str(erro)})


def tela_exemplos():
    """Todos os números da aba 'Exemplos do roteiro', de uma vez só."""
    ex1 = exemplo_1()
    ordem = teste_ordem_das_somas()
    razao = ex1[TRUNCAMENTO]["erros"]["absoluto"] / ex1[ARREDONDAMENTO]["erros"]["absoluto"]
    return json.dumps({
        "ex1": {m: _operacao_para_tela(r) for m, r in ex1.items()},
        "ex1_razao": formatar(ajustar(razao, 2, ARREDONDAMENTO)),
        "ex2": {m: _operacao_para_tela(r) for m, r in exemplo_2().items()},
        "ex3": {m: _somas_para_tela(r) for m, r in exemplo_3().items()},
        "ex3_pdf": {m: _somas_para_tela(r) for m, r in exemplo_3(4, CASAS).items()},
        "divisao": {m: _operacao_para_tela(r) for m, r in teste_divisao().items()},
        "ordem": {
            "grande_primeiro": formatar_maquina(ordem["grande_primeiro"]["aproximado"]),
            "soma_pequenos": formatar_maquina(ordem["soma_pequenos"]["aproximado"]),
            "pequenos_primeiro": formatar_maquina(ordem["pequenos_primeiro"]["aproximado"]),
        },
        "float": [{"conta": conta, "float": repr(f), "decimal": formatar(d)}
                  for conta, f, d in curiosidades_float()],
    })


if __name__ == "__main__":
    # Evita erro de acentuação em terminais antigos do Windows.
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass

    # Atalho para gerar a saída do relatório: python simulador.py --testes
    if "--testes" in sys.argv:
        rodar_todos_os_testes()
    else:
        try:
            menu()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Programa encerrado.\n")
