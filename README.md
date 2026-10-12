# Calculadora de Erros: Simulador de Propagação de Erros Numéricos

**Cálculo Numérico · UNIVASF · Projeto Unidade 1 (Erros) · 2026.2**

Uma calculadora de **precisão limitada**: ela imita uma máquina que só guarda *n* dígitos significativos (no roteiro, *t* = 4) e mostra, para cada conta, o valor exato, o valor aproximado, o erro absoluto e o erro relativo, usando **truncamento** ou **arredondamento**.

**Calculadora online:** https://glaucoe18.github.io/simulador-erros-numericos/ (abre direto no navegador, sem instalar nada)

**Relatório:** [`relatorio/relatorio.pdf`](relatorio/relatorio.pdf)

---

## Como executar

São duas formas de usar, e as duas rodam **o mesmo `simulador.py`**.

### 1. Calculadora no navegador (recomendado)

Abra o link online acima. A página carrega o Python dentro do navegador (com o [Pyodide](https://pyodide.org)) e executa o próprio `simulador.py`; na primeira vez isso leva alguns segundos.

Para rodar a página no seu computador, sirva a pasta com o servidor que já vem no Python (abrir o `index.html` com dois cliques não funciona, porque o navegador bloqueia a leitura do `simulador.py`):

```bash
python -m http.server 8000
```

Depois abra `http://localhost:8000`.

### 2. Menu no terminal (só Python, sem instalar nada)

```bash
python simulador.py
```

```
  1) Nova operação (você escolhe x, y, operação, n e método)
  2) Exemplo 1 - Soma simples (truncamento x arredondamento)
  3) Exemplo 2 - Cancelamento subtrativo
  4) Exemplo 3 - Propagação do erro em 10 somas
  5) Somas sucessivas personalizadas
  6) Rodar todos os testes do relatório
  0) Sair
```

Para imprimir todos os testes de uma vez (é a saída usada no relatório):

```bash
python simulador.py --testes
```

Requisitos: Python 3.10 ou mais novo, só com a biblioteca padrão. A página web precisa de internet para baixar o Pyodide.

---

## Estrutura do projeto

```
simulador.py   ← TODA a matemática + menu do terminal + ponte com a página
index.html     ← estrutura da página (o que aparece na tela)
estilo.css     ← visual da página (cores, fontes, tamanhos)
interface.js   ← comportamento da página: teclado, passo a passo, abas
icones.js      ← desenhos dos ícones (pacote Solar)
relatorio/     ← relatório final em PDF
```

**A página não faz conta nenhuma.** O `interface.js` só lê o que a pessoa digita, chama as funções `tela_...()` do `simulador.py` (parte 9) e desenha o que elas devolvem. Por isso o terminal e a página dão exatamente os mesmos números.

O `simulador.py` está dividido em 9 partes, de cima para baixo:

| Parte | O que faz | Funções principais |
|---|---|---|
| 1 | Configurações (precisão de 50 dígitos, métodos, modos) | — |
| 2 | Lê os números digitados (aceita vírgula) | `ler_numero` |
| 3 | **Ponto flutuante**: normalização, truncamento e arredondamento | `normalizar`, `ajustar` |
| 4 | Operações e erros | `operar`, `calcular_erros` |
| 5 | Simulações completas | `simular_operacao`, `simular_somas_sucessivas` |
| 6 | Exemplos do roteiro e testes extras | `exemplo_1`, `exemplo_2`, `exemplo_3`, ... |
| 7 | Formatação para exibir | `formatar`, `formatar_cientifico`, `formatar_corte` |
| 8 | Menu do terminal | `menu` |
| 9 | Ponte com a página web | `tela_operacao`, `tela_somas`, `tela_exemplos` |

---

## Como o simulador funciona

Para cada operação `x op y` com uma máquina de *n* dígitos:

1. **Valor exato:** a conta é feita com `Decimal` a 50 dígitos de precisão.
2. **Operandos na máquina:** x e y são guardados com *n* dígitos (opcional; é o que o Exemplo 2 pede).
3. **Conta da máquina:** a operação é feita com os operandos guardados.
4. **Normalização e ajuste:** o resultado é escrito como `0.d₁d₂…×10ᵉ` e cortado em *n* dígitos:
   - **truncamento**: descarta o que sobra (`ROUND_DOWN`);
   - **arredondamento**: se o 1º dígito descartado for ≥ 5, soma 1 (`ROUND_HALF_UP`).
5. **Erros:** `Ea = |exato − aprox|` e `Er = Ea / |aprox|` (fórmula do roteiro).

Exemplo de corte com *n* = 4: `1.13572 = 0.1135|72 × 10¹` → truncamento `1.135`, arredondamento `1.136`.

### Decisões que tomamos (e por quê)

- **`Decimal` em vez de `float`.** O float guarda os números em base 2, e por isso 0.29 vira 0.28999999999999998…. No protótipo, truncar 0.29 com 2 dígitos dava **0.28**. Com `Decimal` as contas são feitas em base 10, como no caderno.
- **`ROUND_HALF_UP` em vez de `round()`.** O `round()` do Python faz o "arredondamento bancário" (o empate vai para o dígito par), e aí 0.76545 viraria 0.7654. O roteiro espera **0.7655**.
- **Dois modos de contar os dígitos.** O roteiro pede *t* = 4 **dígitos significativos**, mas no Exemplo 3 o PDF mostra `1.1357`, que tem 4 **casas decimais** (5 dígitos significativos). O simulador tem os dois modos: reproduz o PDF exatamente e também mostra o resultado correto com *t* = 4.

---

## Resultados dos exemplos (*t* = 4)

| Teste | Exato | Truncamento | Arredondamento |
|---|---|---|---|
| **Ex. 1:** 3.14159 + 2.71828 | 5.85987 | 5.859 (Ea = 0.00087, Er = 0.0148%) | 5.860 (Ea = 0.00013, Er = 0.0022%) |
| **Ex. 2:** 0.76545 − 0.76541 | 0.00004 | 0.7654 − 0.7654 = **0** (subtração nula, Er indefinido) | 0.7655 − 0.7654 = 0.0001 (Ea = 0.00006, **Er = 60%**) |
| **Ex. 3:** 0.56786 somado 10× | 5.6786 | 5.671 (Ea = 0.0076, Er = 0.134%) | 5.680 (Ea = 0.0014, Er = 0.0246%) |
| **Ex. 3 como no PDF** (4 casas decimais) | 5.6786 | 5.6781 (Ea = 0.0005) | 5.6789 (Ea = 0.0003) |
| **Extra A:** 2 ÷ 3 | 0.6666… | 0.6666 | 0.6667 |
| **Extra B:** 1000 + 0.4 (10×) | 1004 | grande primeiro: **1000** · pequenos primeiro: **1004** | (idem) |
| **Extra C:** 0.56786 somado 100× | 56.786 | 56.12 (Er = 1.19%) | 56.96 (Er = 0.31%) |

A análise completa de cada caso está no relatório.

---

## Equipe

| Integrante | Participação |
|---|---|
| **Glauco Erasmo** | Finalização do projeto: versão final do código, calculadora web, repositório e relatório |
| **Cristiana Campinho** | Ajustes na finalização do projeto |
| **Alexandre Macedo** | Protótipo inicial em Tkinter (primeira versão da calculadora e dos testes rápidos) e apoio à Cristiana nos ajustes |

## Histórico

A primeira versão foi um protótipo com janela em **Tkinter**, feito pelo **Alexandre Macedo** ([primeiro commit deste repositório](https://github.com/GlaucoE18/simulador-erros-numericos/commit/f24b315c368bf06c26482162969d71639d7173cc)). A versão atual mantém a ideia e as cores do protótipo, e acrescenta:

- contas exatas com `Decimal`;
- a forma normalizada `0.d₁d₂…×10ᵉ`;
- a comparação lado a lado dos dois métodos;
- o passo a passo do Exemplo 3;
- o menu no terminal com a opção "Sair";
- a calculadora web, com o passo a passo de cada função.

Entre as duas, houve uma versão intermediária do painel em Streamlit (está no histórico de commits). Ela foi trocada pela página atual porque o Streamlit não permitia montar um teclado de calculadora nem a animação etapa por etapa.
