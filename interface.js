/* =====================================================================
   CALCULADORA DE ERROS - COMPORTAMENTO DA PÁGINA (interface.js)

   Este arquivo NÃO faz contas. Ele só:
     1. carrega o Python no navegador (Pyodide) e o simulador.py;
     2. lê o que a pessoa digita no teclado da calculadora;
     3. chama as funções tela_...() do simulador.py (PARTE 9 dele);
     4. desenha o resultado, o passo a passo e as outras abas.

   Mapa do arquivo
     PARTE 1 - Utilidades (ícones, formatação de textos)
     PARTE 2 - Python no navegador
     PARTE 3 - Estado da calculadora e teclado
     PARTE 4 - O passo a passo: o que cada etapa explica
     PARTE 5 - Desenho da calculadora e do painel
     PARTE 6 - Animação das etapas (player)
     PARTE 7 - Abas: exemplos, somas sucessivas e código
     PARTE 8 - Eventos (cliques e teclado) e início
   ===================================================================== */


/* =====================================================================
   PARTE 1 - UTILIDADES
   ===================================================================== */

const $ = (id) => document.getElementById(id);

// Ícones do pacote Solar (os desenhos estão em icones.js).
function icone(nome) {
  const desenho = window.ICONES && window.ICONES[nome];
  return desenho ? `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true">${desenho}</svg>` : "";
}
function pintarIcones(raiz = document) {
  raiz.querySelectorAll("[data-ic]").forEach((el) => {
    if (!el.dataset.pintado) { el.insertAdjacentHTML("afterbegin", icone(el.dataset.ic)); el.dataset.pintado = "1"; }
  });
}

const SIMBOLO = { "+": "+", "-": "−", "*": "×", "/": "÷" };
const SOBRESCRITO = { "-": "⁻", "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹" };
const sobrescrito = (k) => String(k).split("").map((c) => SOBRESCRITO[c] || c).join("");

// "0.4 × 10^-4" (como vem do Python)  ->  "0.4 × 10⁻⁴"
const potencia = (texto) => texto.replace(/\^(-?\d+)/g, (_, e) => sobrescrito(e));
const escapar = (t) => String(t).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// Pedacinhos de HTML usados nas explicações
const lin = (html) => `<div class="lin">${html}</div>`;
const nota = (texto) => `<p class="nota">${texto}</p>`;
const str = (t) => `<span class="str">"${escapar(t)}"</span>`;
const num = (t) => `<span class="num">${t}</span>`;
const chamada = (fn, args, retorno) =>
  lin(`<span class="fn">${fn}</span>(${args.join(", ")}) <span class="seta">→</span> ${retorno}`);

// Desenha o corte que vem de separar_corte() do Python: 0.1135|72 × 10¹
function corteHTML(c) {
  if (c.mantidos === "0" && !c.inicio) return "0";
  const sinal = c.sinal ? "−" : "";
  const resto = c.descartados ? `<span class="corte-barra" aria-hidden="true"></span><span class="d">${c.descartados}</span>` : "";
  const exp = c.expoente === null ? "" : ` × 10${sobrescrito(c.expoente)}`;
  return `${sinal}${c.inicio}<span class="k">${c.mantidos}</span>${resto}${exp}`;
}

// Explica a decisão tomada no corte, conforme o método
function decisao(c, metodo) {
  if (!c.descartados) return "cabe inteiro, nada a cortar";
  if (metodo === "truncamento") return `descarta o ${c.descartados}`;
  const d = c.descartados[0];
  return d >= "5" ? `o 1º descartado é ${d} (≥ 5): o último dígito sobe 1` : `o 1º descartado é ${d} (< 5): fica como está`;
}

const descreverPrecisao = (n, modo) => modo === "significativos"
  ? `${n} dígito${n > 1 ? "s" : ""} significativo${n > 1 ? "s" : ""}`
  : `${n} casa${n > 1 ? "s" : ""} decima${n > 1 ? "is" : "l"}`;


/* =====================================================================
   PARTE 2 - PYTHON NO NAVEGADOR
   O Pyodide é o Python compilado para rodar em páginas web. Carregamos
   o simulador.py dentro dele e chamamos as funções tela_...() da PARTE 9.
   ===================================================================== */

const python = { pronto: false, falhou: false, sim: null, codigo: "", linhas: [] };

async function iniciarPython() {
  try {
    const [pyodide, codigo] = await Promise.all([
      loadPyodide({ indexURL: "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/" }),
      fetch("simulador.py").then((resp) => {
        if (!resp.ok) throw new Error("não encontrei o simulador.py");
        return resp.text();
      }),
    ]);
    pyodide.FS.writeFile("simulador.py", codigo);   // coloca o arquivo no "disco" do Python
    pyodide.runPython("import simulador");          // igual a um import normal
    python.sim = pyodide.pyimport("simulador");
    python.codigo = codigo;
    python.linhas = codigo.split("\n");
    python.pronto = true;
    statusPython("pronto", "Python pronto");
    montarLeitorCodigo();
    calcular(false);                                // abre já com o Exemplo 2 calculado
    const abaAberta = document.querySelector('.abas [aria-selected="true"]').dataset.aba;
    if (abaAberta !== "calc") trocarAba(abaAberta);  // atualiza a aba que já estava aberta
  } catch (erro) {
    console.error(erro);
    python.falhou = true;
    statusPython("falhou", "Python não carregou");
    render();
  }
}

// Chama uma função tela_...() do simulador.py e devolve o JSON já convertido
function chamarPython(funcao, ...argumentos) {
  return JSON.parse(python.sim[funcao](...argumentos));
}

function statusPython(classe, texto) {
  $("status-python").className = "status-python " + classe;
  $("status-texto").textContent = texto;
}


/* =====================================================================
   PARTE 3 - ESTADO DA CALCULADORA E TECLADO
   "estado" guarda tudo o que está na tela. Cada tecla muda o estado e
   depois render() redesenha.
   ===================================================================== */

const estado = {
  x: "0.76545", op: "-", y: "0.76541",   // a conta (começa com o Exemplo 2)
  fase: "resultado",                      // "x", "y" ou "resultado"
  n: 4, metodo: "arredondamento", modo: "significativos", ajustarOperandos: true,
  explicacao: "mat",                      // "mat" (matemática) ou "cod" (código)
  resposta: null,                         // o que o Python devolveu
  erro: "",
  etapa: 0,                               // quantas etapas do passo a passo estão visíveis
  encadeado: false,                       // x veio do resultado anterior?
};

const campoAtual = () => (estado.fase === "y" ? "y" : "x");
const entradaValida = (v) => v !== "" && v !== "-";

function tecla(t) {
  pararAnimacao();
  estado.erro = "";

  if (/^[0-9]$/.test(t) || t === ".") {                 // número ou ponto
    if (estado.fase === "resultado") novaConta();
    const campo = campoAtual();
    let valor = estado[campo];
    if (t === "." && valor.includes(".")) return render();
    if (t === "." && !entradaValida(valor)) valor += "0";
    if (valor.replace(/[-.]/g, "").length >= 18) return render();
    if (valor === "0" && t !== ".") valor = "";
    if (valor === "-0" && t !== ".") valor = "-";
    estado[campo] = valor + t;

  } else if (t in SIMBOLO) {                             // + − × ÷
    if (estado.fase === "resultado" && estado.resposta) encadear(t);
    else if (estado.fase === "x" && entradaValida(estado.x)) { estado.op = t; estado.fase = "y"; }
    else if (estado.fase === "y" && estado.y === "") estado.op = t;
    else if (estado.fase === "y" && entradaValida(estado.y)) { calcular(false); if (estado.resposta) encadear(t); }

  } else if (t === "=") {
    if (estado.fase === "y" && entradaValida(estado.y)) return calcular(true);
    if (estado.fase === "resultado" && estado.resposta) return reproduzir();
    return;

  } else if (t === "AC") {
    novaConta();
  } else if (t === "BS") {                               // apagar
    if (estado.fase === "resultado") return;
    const campo = campoAtual();
    if (campo === "y" && estado.y === "") { estado.op = null; estado.fase = "x"; }
    else estado[campo] = estado[campo].slice(0, -1);
  } else if (t === "SIN") {                              // ±
    if (estado.fase === "resultado") return;
    const campo = campoAtual();
    estado[campo] = estado[campo].startsWith("-") ? estado[campo].slice(1) : "-" + estado[campo];
  }
  render();
}

function novaConta() {
  Object.assign(estado, { x: "", op: null, y: "", fase: "x", resposta: null, etapa: 0, encadeado: false });
}

// Apertar uma operação depois do "=" continua a conta a partir do valor da máquina
function encadear(op) {
  Object.assign(estado, { x: estado.resposta.atual.aproximado, op, y: "", fase: "y", resposta: null, encadeado: true });
}

function calcular(comAnimacao) {
  if (!python.pronto) {
    estado.erro = python.falhou ? "O Python não carregou nesta página." : "Aguarde: o Python ainda está carregando.";
    return render();
  }
  const resposta = chamarPython("tela_operacao", estado.x, estado.y, estado.op, estado.n,
                                estado.metodo, estado.modo, estado.ajustarOperandos);
  if (resposta.ok) {
    estado.resposta = resposta;
    estado.fase = "resultado";
    estado.erro = "";
  } else {
    estado.resposta = null;
    estado.erro = resposta.erro;
    if (estado.op) estado.fase = "y";
  }
  montarPassos();
  if (comAnimacao && estado.resposta) reproduzir();
  else { estado.etapa = TOTAL_ETAPAS; aplicarEtapa(); }
  render();
}

// Mudou n, método ou modo: recalcula sem animar
function recalcular() {
  if (estado.fase === "resultado" && python.pronto) calcular(false);
  else { montarPassos(); render(); }
}


/* =====================================================================
   PARTE 4 - O PASSO A PASSO
   Cada etapa diz: qual função está trabalhando, pelo que ela é
   responsável e o que aconteceu com os números. No modo "Código"
   aparece também a chamada real e as linhas do simulador.py.
   ===================================================================== */

const TOTAL_ETAPAS = 6;

// Resumo de cada etapa (aparece antes de apertar "=")
const ROTEIRO = [
  { titulo: "Conta exata", funcao: "operar()", resumo: "calcula o valor de referência, sem limitar os dígitos" },
  { titulo: "x e y entram na máquina", funcao: "ajustar()", resumo: "guarda x e y com n dígitos" },
  { titulo: "A máquina faz a conta", funcao: "operar()", resumo: "repete a conta com os valores guardados" },
  { titulo: "Normaliza e corta o resultado", funcao: "ajustar()", resumo: "mantém só n dígitos do resultado" },
  { titulo: "Calcula os erros", funcao: "calcular_erros()", resumo: "compara o exato com o aproximado" },
  { titulo: "Mostra na tela", funcao: "tela_operacao()", resumo: "manda os números prontos para a página" },
];

// Linhas de operar() que rodam para cada operação
const LINHAS_OPERAR = {
  "+": ['if op == "+":', "return x + y"],
  "-": ['if op == "-":', "return x - y"],
  "*": ['if op == "*":', "return x * y"],
  "/": ["if y == 0:", "return x / y"],
};

function montarEtapas(a) {
  const s = a.simbolo, prec = a.precisao, trunc = a.metodo === "truncamento", sig = a.modo === "significativos";
  const metodoTxt = trunc
    ? "<strong>truncamento</strong>: os dígitos que passam da barra são simplesmente jogados fora"
    : "<strong>arredondamento</strong>: a função olha o primeiro dígito depois da barra e, se ele for 5 ou mais, soma 1 no último dígito guardado";
  const args = (nome) => [nome, num(a.n), str(a.metodo), str(a.modo)];
  const etapas = [];

  // 1. Conta exata
  etapas.push({
    agora: `Agora a função <code>operar()</code> faz a conta <strong>${a.x} ${s} ${a.y}</strong> sem limitar os dígitos: ela usa o tipo Decimal, com 50 dígitos de precisão. Esse é o <strong>valor exato</strong> do roteiro, a referência para medir o erro.`,
    mat: lin(`${a.x} ${s} ${a.y} = <b>${a.exato}</b>`) + nota(`Forma normalizada: ${potencia(a.exato_normalizado)}`),
    cod: chamada("operar", [`Decimal(${str(a.x)})`, `Decimal(${str(a.y)})`, str(a.op)], `Decimal(${str(a.exato)})`),
    trecho: ["operar", LINHAS_OPERAR[a.op]],
  });

  // 2. Operandos na máquina
  if (a.ajustar_operandos) {
    const operando = (nome, original, corte, maquina) =>
      lin(`<span class="rot">${nome} =</span> ${original} = ${corteHTML(corte)} → <b>${maquina}</b>`) + nota(decisao(corte, a.metodo));
    etapas.push({
      agora: `Agora <code>simular_operacao()</code> chama a função <code>ajustar()</code> duas vezes, uma para x e outra para y. Ela é responsável por guardar cada número como a máquina guardaria: com <strong>${prec}</strong>. O método escolhido é ${metodoTxt}.`,
      mat: operando("x", a.x, a.x_corte, a.x_maquina) + operando("y", a.y, a.y_corte, a.y_maquina),
      cod: chamada("ajustar", args("x"), a.x_maquina) + chamada("ajustar", args("y"), a.y_maquina),
      trecho: ["simular_operacao", ["x_maquina = ajustar(x, n, metodo, modo)", "y_maquina = ajustar(y, n, metodo, modo)"]],
    });
  } else {
    etapas.push({
      agora: `Esta etapa foi <strong>pulada</strong>: a opção "Guardar x e y com n dígitos" está desligada, então <code>simular_operacao()</code> usa x e y inteiros e só o resultado será cortado.`,
      mat: lin(`x = <b>${a.x}</b>   y = <b>${a.y}</b>`),
      cod: lin(`ajustar_operandos = <span class="num">False</span>  <span class="seta">→</span> x_maquina, y_maquina = x, y`),
      trecho: ["simular_operacao", ["x_maquina, y_maquina = x, y"]],
    });
  }

  // 3. Conta da máquina
  etapas.push({
    agora: a.ajustar_operandos
      ? `Agora <code>operar()</code> é chamada de novo, mas com os números <strong>que a máquina guardou</strong> (${a.x_maquina} e ${a.y_maquina}), e não com os originais. É aqui que o erro da etapa 2 entra na conta.`
      : `Agora <code>operar()</code> é chamada de novo com x e y. Como eles não foram cortados, esta conta é igual à exata.`,
    mat: lin(`${a.x_maquina} ${s} ${a.y_maquina} = <b>${a.bruto}</b>`) + nota("Resultado bruto: ainda pode ter mais dígitos do que cabem na máquina."),
    cod: chamada("operar", ["x_maquina", "y_maquina", str(a.op)], a.bruto),
    trecho: ["simular_operacao", ["resultado_bruto = operar(x_maquina, y_maquina, op)"]],
  });

  // 4. Normaliza e corta
  const zero = a.bruto === "0";
  etapas.push({
    agora: sig
      ? `Agora <code>ajustar()</code> trabalha no resultado. Primeiro ele é escrito na forma normalizada 0.d₁d₂… × 10ᵉ; depois a função mantém só <strong>${prec}</strong>. O método é ${metodoTxt}.`
      : `Agora <code>ajustar()</code> trabalha no resultado e mantém só <strong>${prec}</strong> depois do ponto. O método é ${metodoTxt}.`,
    mat: zero
      ? lin(`0 → <b>0</b>`) + nota("O resultado deu 0. O zero não tem forma normalizada (não existe d₁ ≠ 0), então a máquina guarda 0.")
      : lin(`${a.bruto} = ${corteHTML(a.bruto_corte)}`) + lin(`<span class="rot">${decisao(a.bruto_corte, a.metodo)}</span> → <b>${a.aproximado}</b>`)
        + nota(`Valor guardado na forma normalizada: ${potencia(a.aproximado_normalizado)}`),
    cod: chamada("ajustar", args("resultado_bruto"), a.aproximado) + nota(`Dentro dela: valor.quantize(..., rounding=${trunc ? "ROUND_DOWN" : "ROUND_HALF_UP"})`),
    trecho: ["ajustar", sig
      ? ["regra = ROUND_DOWN if metodo == TRUNCAMENTO else ROUND_HALF_UP", "posicao_ultimo = valor.adjusted() - (n - 1)",
         "resultado = valor.quantize(Decimal(1).scaleb(posicao_ultimo), rounding=regra)"]
      : ["regra = ROUND_DOWN if metodo == TRUNCAMENTO else ROUND_HALF_UP", "resultado = valor.quantize(Decimal(1).scaleb(-n), rounding=regra)"]],
  });

  // 5. Erros
  etapas.push({
    agora: `Agora a função <code>calcular_erros()</code> compara o valor exato (etapa 1) com o aproximado (etapa 4), usando as fórmulas do roteiro: <strong>Ea = |exato − aprox|</strong> e <strong>Er = Ea / |aprox|</strong>.`,
    mat: lin(`Ea = |${a.exato} − ${a.aproximado}| = <b>${a.ea}</b>`) + (a.er_indefinido
      ? lin(`Er = ${a.ea} ÷ 0 → <b>indefinido</b>`) + nota(a.sem_erro ? "Não houve erro nenhum (Ea = 0), mas a fórmula do roteiro divide por zero." : "Não existe divisão por zero: com o aproximado igual a 0, o erro relativo não pode ser calculado.")
      : lin(`Er = ${a.ea} ÷ |${a.aproximado}| = <b>${a.er}</b> = <b>${a.er_pct}</b>`)),
    cod: chamada("calcular_erros", ["exato", "aproximado"], `{${str("absoluto")}: ${a.ea}, ${str("relativo")}: ${a.er_indefinido ? "None" : a.er}}`),
    trecho: ["calcular_erros", ["absoluto = abs(exato - aproximado)", "relativo = absoluto / abs(aproximado) if aproximado != 0 else None"]],
  });

  // 6. Tela
  etapas.push({
    agora: `Por fim, <code>simular_operacao()</code> junta tudo num dicionário e <code>tela_operacao()</code> (parte 9) transforma os números em texto e manda para a página. O JavaScript só desenha: o visor recebe <strong>${a.aproximado}</strong> e este painel recebe os erros.`,
    mat: lin(`visor: <b>${a.aproximado}</b>   ·   Ea = ${a.ea}   ·   Er = ${a.er_pct}`),
    cod: chamada("tela_operacao", [str(a.x), str(a.y), str(a.op), num(a.n), str(a.metodo), str(a.modo), num(a.ajustar_operandos ? "True" : "False")], `JSON {${str("atual")}, ${str("outro")}}`),
    trecho: ["tela_operacao", ["r = simular_operacao(x, y, op, n, metodo, modo, bool(ajustar_operandos))",
                               "r_outro = simular_operacao(x, y, op, n, outro, modo, bool(ajustar_operandos))",
                               'return json.dumps({"ok": True, "atual": _operacao_para_tela(r),']],
  });

  return etapas.map((e, i) => ({ ...ROTEIRO[i], ...e, titulo: i === 3 && !sig ? "Corta o resultado" : ROTEIRO[i].titulo }));
}

// Pega no simulador.py as linhas que rodam nesta etapa (com o número de cada linha)
function trechoHTML(nomeFuncao, marcadores) {
  if (!python.linhas.length) return "";
  const inicio = python.linhas.findIndex((l) => l.startsWith(`def ${nomeFuncao}(`));
  if (inicio < 0) return "";
  let fim = python.linhas.findIndex((l, i) => i > inicio && /^\S/.test(l));
  if (fim < 0) fim = python.linhas.length;
  const escolhidas = new Set([inicio]);
  marcadores.forEach((m) => {
    const i = python.linhas.findIndex((l, k) => k > inicio && k < fim && l.includes(m));
    if (i >= 0) escolhidas.add(i);
  });
  const ordem = [...escolhidas].sort((a, b) => a - b);
  let html = "", anterior = null;
  ordem.forEach((i) => {
    if (anterior !== null && i > anterior + 1) html += `<span class="reticencias">⋯</span>`;
    const linha = python.linhas[i];
    const colorida = window.hljs ? hljs.highlight(linha, { language: "python", ignoreIllegals: true }).value : escapar(linha);
    html += `<span class="l${i === inicio ? "" : " destaque"}"><span class="nl">${i + 1}</span>${colorida}</span>`;
    anterior = i;
  });
  const alvo = ordem.find((i) => i !== inicio) ?? inicio;
  return `<figure class="trecho"><div class="trecho-cab"><span>simulador.py · ${nomeFuncao}()</span>
    <button data-linha="${alvo + 1}">${icone("code-2-linear")}ver no código</button></div><pre>${html}</pre></figure>`;
}

// Monta a lista de etapas (uma vez por resultado ou troca de modo)
function montarPassos() {
  const lista = $("passos");
  if (!estado.resposta) {
    lista.innerHTML = ROTEIRO.map((r, i) => `<li class="pendente"><span class="marcador">${i + 1}</span><div>
      <p class="passo-titulo">${i === 3 && estado.modo === "casas" ? "Corta o resultado" : r.titulo}<span class="chip-funcao">${r.funcao}</span></p>
      <p class="nota">${r.resumo}</p></div></li>`).join("");
    return;
  }
  const etapas = montarEtapas(estado.resposta.atual);
  lista.innerHTML = etapas.map((e, i) => `<li class="pendente" data-etapa="${i + 1}"><span class="marcador">${i + 1}</span><div>
      <p class="passo-titulo">${e.titulo}<span class="chip-funcao">${e.funcao}</span></p>
      <div class="passo-corpo"><div>
        <p class="agora">${e.agora}</p>
        <div class="quadro">${estado.explicacao === "cod" ? e.cod : e.mat}</div>
        ${estado.explicacao === "cod" ? trechoHTML(...e.trecho) : ""}
      </div></div></div></li>`).join("");
  aplicarEtapa();
}


/* =====================================================================
   PARTE 5 - DESENHO DA CALCULADORA E DO PAINEL
   ===================================================================== */

function render() {
  // começou uma conta nova: a lista volta a mostrar o plano das etapas
  if (!estado.resposta && document.querySelector("#passos > li[data-etapa]")) montarPassos();

  // botões de configuração
  $("n-valor").textContent = estado.n;
  document.querySelectorAll("[data-metodo]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.metodo === estado.metodo));
  document.querySelectorAll("[data-modo]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.modo === estado.modo));
  $("chave-operandos").setAttribute("aria-checked", estado.ajustarOperandos);
  document.querySelectorAll(".tecla.op").forEach((b) =>
    b.setAttribute("aria-pressed", estado.fase === "y" && estado.y === "" && b.dataset.t === estado.op));
  $("modo-mat").setAttribute("aria-pressed", estado.explicacao === "mat");
  $("modo-cod").setAttribute("aria-pressed", estado.explicacao === "cod");

  renderVisor();
  renderPainel();
}

function renderVisor() {
  const a = estado.resposta && estado.resposta.atual;
  const op = estado.op ? ` ${SIMBOLO[estado.op]} ` : "";
  $("visor-maq").textContent = `máquina de ${estado.n} ${estado.modo === "significativos" ? "díg. signif." : "casas dec."} · ${estado.metodo}`;
  $("visor-fase").textContent = estado.fase === "resultado" ? "resultado" : estado.fase === "y" ? "digitando y" : "digitando x";
  const numero = $("visor-num");
  numero.classList.remove("carregando");

  if (estado.fase === "resultado" && a) {
    $("visor-expr").textContent = `${a.x} ${a.simbolo} ${a.y} =`;
    numero.textContent = a.aproximado;
    $("visor-rodape").innerHTML = `<span>exato <b>${a.exato}</b></span><span class="er">Er <b>${textoErroRelativo(a)}</b></span>`;
    return;
  }
  if (!python.pronto && estado.fase === "resultado") {
    $("visor-expr").textContent = "";
    numero.classList.add("carregando");
    numero.textContent = python.falhou ? "Não foi possível carregar o Python." : "Carregando o Python no navegador…";
    $("visor-rodape").innerHTML = `<span>${python.falhou ? "Sem internet? Use o terminal: python simulador.py" : "na primeira vez leva alguns segundos"}</span>`;
    return;
  }
  const atual = campoAtual() === "y" ? estado.y : estado.x;
  $("visor-expr").textContent = estado.fase === "y" ? `${estado.x}${op}` : "";
  numero.innerHTML = `${escapar(atual || "0")}<span class="cursor"></span>`;
  $("visor-rodape").innerHTML = estado.erro
    ? `<span style="color:var(--vermelho)">${escapar(estado.erro)}</span>`
    : `<span>${estado.fase === "y" ? "digite y e aperte =" : "digite x e escolha a operação"}</span>`;
}

function renderPainel() {
  const r = estado.resposta;
  $("player").hidden = !r;
  if (!r) {
    $("resultado").innerHTML = "";
    const x = estado.x || "x", y = estado.y || "y", op = estado.op ? SIMBOLO[estado.op] : "?";
    let texto;
    if (estado.erro) texto = `<b style="color:var(--vermelho)">${escapar(estado.erro)}</b> Corrija o número e aperte = de novo.`;
    else if (!python.pronto) texto = python.falhou
      ? "O Python não carregou nesta página. Verifique a internet ou use o terminal: <b>python simulador.py</b>."
      : "Carregando o simulador.py dentro do navegador…";
    else texto = `Você vai calcular <b>${escapar(x)} ${op} ${escapar(y)}</b> numa máquina que guarda <b>${descreverPrecisao(estado.n, estado.modo)}</b>, usando <b>${estado.metodo}</b>.`
      + (estado.encadeado ? " O x veio do resultado anterior, já com o erro dele." : "")
      + " Ao apertar <b>=</b>, o programa chama estas funções do simulador.py, nesta ordem:";
    $("plano").innerHTML = texto;
    return;
  }
  $("plano").innerHTML = "";
  const a = r.atual, b = r.outro;
  const linha = (m, ativo) => `<tr class="${ativo ? "ativo" : ""}"><td><span class="ponto"></span>${m.metodo[0].toUpperCase() + m.metodo.slice(1)}</td><td>${m.aproximado}</td><td>${m.ea}</td><td>${m.er}</td><td>${m.er_pct}</td></tr>`;
  const [t, ar] = a.metodo === "truncamento" ? [a, b] : [b, a];
  const erTexto = textoErroRelativo(a);
  $("resultado").innerHTML = `
    <div class="stats">
      <div class="stat"><div class="rot">Valor exato</div><div class="val">${a.exato}</div><div class="extra">${potencia(a.exato_normalizado)}</div></div>
      <div class="stat"><div class="rot">Valor aproximado</div><div class="val menta">${a.aproximado}</div><div class="extra">${potencia(a.aproximado_normalizado)}</div></div>
      <div class="stat"><div class="rot">Erro absoluto</div><div class="val erro">${a.ea}</div><div class="extra">|exato − aprox|</div></div>
      <div class="stat"><div class="rot">Erro relativo</div><div class="val ${a.er_indefinido && !a.sem_erro ? "indef" : "erro"}">${erTexto}</div><div class="extra">${a.er_indefinido ? "o aproximado deu 0" : "Er = " + a.er}</div></div>
    </div>
    <div class="comparacao-wrap"><table class="comparacao"><thead><tr><th>Método</th><th>Aproximado</th><th>Erro absoluto</th><th>Erro relativo</th><th>Er (%)</th></tr></thead>
      <tbody>${linha(t, t === a)}${linha(ar, ar === a)}</tbody></table></div>
    ${conclusao(a)}`;
}

// 0 - 0: Er seria 0/0, mas não houve erro nenhum
const textoErroRelativo = (a) => (a.er_indefinido ? (a.sem_erro ? "sem erro" : "indefinido") : a.er_pct);

function conclusao(a) {
  const caixa = (tipo, ic, titulo, texto) => `<div class="conclusao ${tipo}">${icone(ic)}<div><strong>${titulo}</strong>${texto}</div></div>`;
  if (a.aproximado_zero && !a.exato_zero)
    return caixa("critico", "danger-triangle-linear", a.op === "-" ? "Subtração nula" : "O resultado virou zero",
      a.op === "-" ? "x e y ficaram iguais dentro da máquina e a resposta virou 0. Perdemos o resultado inteiro, e o erro relativo nem pode ser calculado."
                   : "O resultado é pequeno demais para a quantidade de casas guardadas, e a máquina guardou 0.");
  if (a.op === "-" && a.er_alto)
    return caixa("alerta", "danger-triangle-linear", `Cancelamento subtrativo: erro relativo de ${a.er_pct}`,
      "x e y são muito próximos. Os dígitos iguais se cancelaram e sobrou só o final, que é justamente a parte com erro.");
  if (a.sem_erro)
    return caixa("ok", "check-circle-linear", "Sem erro", `O resultado cabe inteiro em ${a.precisao}.`);
  return caixa("neutro", "info-circle-linear", `Erro relativo de ${a.er_pct}`, a.metodo === "truncamento"
    ? "O truncamento sempre leva o número para mais perto do zero; compare com o arredondamento na tabela."
    : "O arredondamento escolhe o valor guardável mais próximo: o erro do corte fica em no máximo meia unidade do último dígito.");
}


/* =====================================================================
   PARTE 6 - ANIMAÇÃO DAS ETAPAS (player)
   Ao apertar "=", as etapas acendem uma de cada vez. Também dá para
   andar etapa por etapa com as setas, bom para explicar ao vivo.
   ===================================================================== */

let temporizador = null, primeiroQuadro = null;
const VELOCIDADE = 1100;   // milissegundos por etapa

function aplicarEtapa() {
  document.querySelectorAll("#passos > li[data-etapa]").forEach((li) => {
    const k = Number(li.dataset.etapa);
    li.className = k < estado.etapa || estado.etapa === TOTAL_ETAPAS ? "feito" : k === estado.etapa ? "atual" : "pendente";
  });
  const atual = ROTEIRO[Math.max(0, estado.etapa - 1)];
  $("contador").innerHTML = estado.etapa === 0 ? "Pronto para começar"
    : `Etapa <b>${estado.etapa}</b> de ${TOTAL_ETAPAS} · <span class="chip-funcao">${atual.funcao}</span>`;
  $("etapa-anterior").disabled = estado.etapa <= 1;
  $("etapa-proxima").disabled = estado.etapa >= TOTAL_ETAPAS;
}

function pararAnimacao() {
  clearInterval(temporizador); cancelAnimationFrame(primeiroQuadro);
  temporizador = primeiroQuadro = null;
}

function reproduzir() {
  pararAnimacao();
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) { estado.etapa = TOTAL_ETAPAS; return aplicarEtapa(); }
  estado.etapa = 0;
  aplicarEtapa();
  primeiroQuadro = requestAnimationFrame(() => { estado.etapa = 1; aplicarEtapa(); });
  temporizador = setInterval(() => {
    estado.etapa++;
    aplicarEtapa();
    if (estado.etapa >= TOTAL_ETAPAS) pararAnimacao();
  }, VELOCIDADE);
}

function irEtapa(delta) {
  pararAnimacao();
  estado.etapa = Math.min(TOTAL_ETAPAS, Math.max(1, estado.etapa + delta));
  aplicarEtapa();
  const li = document.querySelector(`#passos > li[data-etapa="${estado.etapa}"]`);
  if (li) li.scrollIntoView({ block: "nearest", behavior: "smooth" });
}


/* =====================================================================
   PARTE 7 - ABAS: EXEMPLOS, SOMAS SUCESSIVAS E CÓDIGO
   ===================================================================== */

const ABAS = ["calc", "exemplos", "somas", "codigo", "teoria"];

function trocarAba(nome) {
  if (!ABAS.includes(nome)) nome = "calc";
  history.replaceState(null, "", nome === "calc" ? location.pathname + location.search : "#" + nome);  // link direto para a aba
  document.querySelectorAll(".abas [role=tab]").forEach((b) => b.setAttribute("aria-selected", b.dataset.aba === nome));
  ABAS.forEach((a) => { $("aba-" + a).hidden = a !== nome; });
  if (nome === "exemplos") renderExemplos();
  if (nome === "somas") renderSomas();
}

// ---------- Exemplos do roteiro ----------
function renderExemplos() {
  if (!python.pronto) return;
  const e = chamarPython("tela_exemplos");
  const T = "truncamento", A = "arredondamento";
  const linha = (rotulo, valor) => `<div><span>${rotulo}</span><span>${valor}</span></div>`;
  const dupla = (r1, v1, r2, v2, cor1 = "", cor2 = "") =>
    `<div class="duplas"><div><div class="rot">${r1}</div><div class="grande" style="${cor1}">${v1}</div></div><div><div class="rot">${r2}</div><div class="grande" style="${cor2}">${v2}</div></div></div>`;
  const ex1 = e.ex1, ex2 = e.ex2, ex3 = e.ex3, pdf = e.ex3_pdf, dv = e.divisao;
  $("grade-ex").innerHTML = `
    <article class="card-ex"><span class="tag">${icone("add-circle-linear")}Exemplo 1 · soma simples</span>
      <h3>3.14159 + 2.71828</h3>
      ${dupla("Truncamento", ex1[T].aproximado, "Arredondamento", ex1[A].aproximado)}
      <div class="mini-linhas">${linha("Exato", ex1[T].exato)}${linha("Erro absoluto", `${ex1[T].ea} · ${ex1[A].ea}`)}${linha("Erro relativo", `${ex1[T].er_pct} · ${ex1[A].er_pct}`)}</div>
      <p>O truncamento leva o número para baixo; o arredondamento escolhe o valor mais próximo e, aqui, erra ${e.ex1_razao.replace(".", ",")} vezes menos.</p>
      <div class="rodape"><button class="botao" data-preset="ex1">Abrir na calculadora ${icone("arrow-right-linear")}</button></div></article>

    <article class="card-ex"><span class="tag">${icone("danger-triangle-linear")}Exemplo 2 · cancelamento subtrativo</span>
      <h3>0.76545 − 0.76541</h3>
      ${dupla("Erro relativo, arredondando", ex2[A].er_pct, "Resultado, truncando", ex2[T].aproximado, "color:var(--laranja)", "color:var(--vermelho)")}
      <div class="mini-linhas">${linha("Exato", ex2[A].exato)}${linha("Arredondados", `${ex2[A].x_maquina} − ${ex2[A].y_maquina}`)}${linha("Truncados", `${ex2[T].x_maquina} − ${ex2[T].y_maquina}`)}</div>
      <p>Truncando, x e y ficam iguais e a subtração vira zero: é a subtração nula que o roteiro pede para demonstrar.</p>
      <div class="rodape"><button class="botao" data-preset="ex2">Abrir na calculadora ${icone("arrow-right-linear")}</button></div></article>

    <article class="card-ex"><span class="tag">${icone("repeat-linear")}Exemplo 3 · 10 somas de 0.56786</span>
      <h3>Exato: ${ex3[T].exato}</h3>
      ${dupla("Truncamento", ex3[T].aproximado, "Arredondamento", ex3[A].aproximado)}
      <div class="mini-linhas">${linha("Erro absoluto", `${ex3[T].ea} · ${ex3[A].ea}`)}${linha("Erro relativo", `${ex3[T].er_pct} · ${ex3[A].er_pct}`)}${linha("Como no PDF (4 casas)", `${pdf[T].aproximado} · ${pdf[A].aproximado}`)}</div>
      <p>O PDF mostra 1.1357, 1.7035…: são 4 casas decimais. Com 4 dígitos significativos, a primeira soma fica 1.135.</p>
      <div class="rodape"><button class="botao" data-ir-somas="ex3">Ver passo a passo ${icone("arrow-right-linear")}</button><button class="botao fantasma" data-ir-somas="ex3-pdf">Como no PDF</button></div></article>

    <article class="card-ex"><span class="tag">${icone("test-tube-linear")}Teste extra · divisão</span>
      <h3>2 ÷ 3</h3>
      ${dupla("Truncamento", dv[T].aproximado, "Arredondamento", dv[A].aproximado)}
      <div class="mini-linhas">${linha("Erro absoluto", `${dv[T].ea} · ${dv[A].ea}`)}</div>
      <p>Uma dízima nunca cabe numa máquina finita. Arredondando, o erro cai pela metade.</p>
      <div class="rodape"><button class="botao fantasma" data-preset="div">Abrir na calculadora</button></div></article>

    <article class="card-ex"><span class="tag">${icone("sort-vertical-linear")}Teste extra · ordem das somas</span>
      <h3>1000 + 0.4 + 0.4 + … (10×)</h3>
      ${dupla("1000 primeiro", e.ordem.grande_primeiro, "0.4 primeiro", e.ordem.pequenos_primeiro, "color:var(--vermelho)", "color:var(--menta)")}
      <p>Com 4 dígitos, 1000.4 não cabe e volta a ser 1000 a cada soma. Somando os 0.4 primeiro (${e.ordem.soma_pequenos}), dá o exato, 1004. Na máquina, a soma não é associativa.</p>
      <div class="rodape"><button class="botao fantasma" data-ir-somas="ordem">Ver as somas</button></div></article>

    <article class="card-ex"><span class="tag">${icone("cpu-linear")}Teste extra · o float também erra</span>
      <h3>As mesmas contas em float</h3>
      <div class="mini-linhas">${e.float.map((f) => linha(f.conta, `${f.float}<br><span style="color:var(--menta)">Decimal: ${f.decimal}</span>`)).join("")}</div>
      <p>O float guarda os números em base 2, onde 0.1 e 0.29 não têm representação exata. Por isso o simulador usa Decimal, que conta em base 10.</p></article>`;
}

// ---------- Somas sucessivas ----------
const somas = { ajustarParcela: false };

function renderSomas() {
  $("chave-parcela").setAttribute("aria-checked", somas.ajustarParcela);
  $("s-maquina").textContent = `Máquina atual: ${descreverPrecisao(estado.n, estado.modo)}. O n e o modo são os da calculadora.`;
  if (!python.pronto) return;
  const r = chamarPython("tela_somas", $("s-parcela").value, $("s-qtd").value, estado.n, estado.modo,
                         $("s-inicial").value, somas.ajustarParcela);
  $("s-erro").textContent = r.ok ? "" : r.erro;
  if (!r.ok) return;
  const t = r.truncamento, a = r.arredondamento;
  const resumo = (rotulo, x, cor) => `<div class="stat"><div class="rot">${rotulo}</div><div class="val" style="color:${cor}">${x.aproximado}</div><div class="extra">exato ${x.exato} · Ea ${x.ea} · Er ${x.er_pct}</div></div>`;
  $("resumo-somas").innerHTML = resumo("Truncamento", t, "var(--laranja)") + resumo("Arredondamento", a, "var(--menta)");
  $("grafico").innerHTML = grafico([
    { cor: "#ff8a4c", y: t.passos.map((p) => p.erro_numero) },
    { cor: "#4cf0b0", y: a.passos.map((p) => p.erro_numero) },
  ]);
  const linhas = t.passos.map((p, k) => {
    const q = a.passos[k];
    return `<tr><td>${p.passo}</td><td>${p.exato}</td><td>${p.guardado}</td><td style="color:var(--laranja)">${p.erro}</td><td>${q.guardado}</td><td style="color:var(--menta)">${q.erro}</td></tr>`;
  });
  $("tabela-somas").innerHTML = `<thead><tr><th>Soma</th><th>Exato</th><th>Truncamento</th><th>Erro</th><th>Arredondamento</th><th>Erro</th></tr></thead>
    <tbody>${linhas.join("") || `<tr><td colspan="6">Com 1 parcela não há somas.</td></tr>`}</tbody>`;
}

// Gráfico de linhas simples, desenhado em SVG
function grafico(series) {
  const W = 640, H = 262, ml = 60, mr = 14, mt = 12, mb = 42, n = series[0].y.length;
  if (!n) return `<p class="sub">Nada para desenhar: com 1 parcela não há somas.</p>`;
  const max = Math.max(...series.flatMap((s) => s.y), 1e-12);
  const X = (i) => ml + (n === 1 ? (W - ml - mr) / 2 : (i / (n - 1)) * (W - ml - mr));
  const Y = (v) => mt + (1 - v / max) * (H - mt - mb);
  const fonte = `fill="#5c6471" font-size="10.5" font-family="JetBrains Mono, monospace"`;
  const grade = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const v = max * f, y = Y(v);
    return `<line x1="${ml}" x2="${W - mr}" y1="${y}" y2="${y}" stroke="#262a31"/><text x="${ml - 8}" y="${y + 4}" text-anchor="end" ${fonte}>${Number(v.toPrecision(2))}</text>`;
  }).join("");
  const passo = Math.max(1, Math.ceil(n / 8));
  const eixoX = [...Array(n).keys()].filter((i) => i % passo === 0 || i === n - 1)
    .map((i) => `<text x="${X(i)}" y="${H - 24}" text-anchor="middle" ${fonte}>${i + 1}</text>`).join("");
  const linhas = series.map((s) => {
    const d = s.y.map((v, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join(" ");
    return `<path d="${d}" fill="none" stroke="${s.cor}" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round"/><circle cx="${X(n - 1)}" cy="${Y(s.y[n - 1])}" r="4" fill="${s.cor}"/>`;
  }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Erro absoluto acumulado a cada soma">${grade}${eixoX}${linhas}
    <text x="${(W + ml) / 2}" y="${H - 4}" text-anchor="middle" fill="#5c6471" font-size="10" font-family="Plus Jakarta Sans, sans-serif">número da soma</text></svg>`;
}

function presetSomas(nome) {
  const valores = { ex3: ["0.56786", "10", ""], "ex3-pdf": ["0.56786", "10", ""], cem: ["0.56786", "100", ""], ordem: ["0.4", "10", "1000"] }[nome];
  if (!valores) return;
  [$("s-parcela").value, $("s-qtd").value, $("s-inicial").value] = valores;
  somas.ajustarParcela = false;
  if (nome === "ex3-pdf") Object.assign(estado, { modo: "casas", n: 4 });
  if (nome === "ex3" || nome === "cem" || nome === "ordem") Object.assign(estado, { modo: "significativos", n: 4 });
  recalcular();
  trocarAba("somas");
}

// ---------- Código ----------
function montarLeitorCodigo() {
  const linhas = python.linhas;
  $("leitor-numeros").textContent = linhas.map((_, i) => i + 1).join("\n");
  $("leitor-codigo").innerHTML = window.hljs
    ? hljs.highlight(python.codigo, { language: "python", ignoreIllegals: true }).value
    : escapar(python.codigo);
  $("leitor-info").textContent = `${linhas.length} linhas`;

  // índice: as PARTES do arquivo e as funções de cada uma
  let html = "";
  linhas.forEach((l, i) => {
    const parte = l.match(/^# PARTE (\d+) - (.+)$/);
    const funcao = l.match(/^def ([a-zA-Z]\w*)\(/);
    if (parte) html += `<h3>${parte[1]}. ${escapar(parte[2].charAt(0) + parte[2].slice(1).toLowerCase())}</h3>`;
    else if (funcao) html += `<button data-linha="${i + 1}">${funcao[1]}()</button>`;
  });
  $("indice-codigo").innerHTML = html;
}

function irParaLinha(numero) {
  trocarAba("codigo");
  const corpo = $("leitor-corpo"), codigo = $("leitor-codigo");
  const altura = parseFloat(getComputedStyle(codigo).lineHeight) || 21;
  const topo = 12 + (numero - 1) * altura;
  const marca = $("marca-linha");
  marca.hidden = false;
  marca.style.top = `${topo}px`;
  corpo.scrollTo({ top: Math.max(0, topo - 120), behavior: "smooth" });
  $("leitor-info").textContent = `linha ${numero} de ${python.linhas.length}`;
  document.querySelector(".leitor").scrollIntoView({ block: "start", behavior: "smooth" });
}


/* =====================================================================
   PARTE 8 - EVENTOS E INÍCIO
   ===================================================================== */

function preset(nome) {
  const p = { ex1: ["3.14159", "+", "2.71828"], ex2: ["0.76545", "-", "0.76541"], div: ["2", "/", "3"] }[nome];
  Object.assign(estado, { x: p[0], op: p[1], y: p[2], n: 4, modo: "significativos", ajustarOperandos: true, encadeado: false });
  trocarAba("calc");
  calcular(true);
}

document.addEventListener("click", (ev) => {
  const b = ev.target.closest("button");
  if (!b) return;
  if (b.dataset.t) tecla(b.dataset.t);
  else if (b.dataset.aba) trocarAba(b.dataset.aba);
  else if (b.dataset.preset) preset(b.dataset.preset);
  else if (b.dataset.irSomas) presetSomas(b.dataset.irSomas);
  else if (b.dataset.somas) presetSomas(b.dataset.somas);
  else if (b.dataset.linha) irParaLinha(Number(b.dataset.linha));
  else if (b.dataset.metodo) { estado.metodo = b.dataset.metodo; recalcular(); }
  else if (b.dataset.modo) { estado.modo = b.dataset.modo; recalcular(); }
  else if (b.id === "n-menos" && estado.n > 1) { estado.n--; recalcular(); }
  else if (b.id === "n-mais" && estado.n < 15) { estado.n++; recalcular(); }
  else if (b.id === "chave-operandos") { estado.ajustarOperandos = !estado.ajustarOperandos; recalcular(); }
  else if (b.id === "chave-parcela") { somas.ajustarParcela = !somas.ajustarParcela; renderSomas(); }
  else if (b.id === "modo-mat" || b.id === "modo-cod") { estado.explicacao = b.id === "modo-cod" ? "cod" : "mat"; montarPassos(); render(); }
  else if (b.id === "reproduzir") reproduzir();
  else if (b.id === "etapa-anterior") irEtapa(-1);
  else if (b.id === "etapa-proxima") irEtapa(+1);
});

["s-parcela", "s-qtd", "s-inicial"].forEach((id) => $(id).addEventListener("input", renderSomas));

// Teclado do computador também funciona na calculadora
document.addEventListener("keydown", (ev) => {
  if ($("aba-calc").hidden || ev.target.matches("input, textarea") || ev.ctrlKey || ev.metaKey || ev.altKey) return;
  const mapa = { Enter: "=", "=": "=", Backspace: "BS", Escape: "AC", Delete: "AC", ",": ".", ".": ".",
                 "+": "+", "-": "-", "*": "*", x: "*", "/": "/" };
  const t = /^[0-9]$/.test(ev.key) ? ev.key : mapa[ev.key];
  if (!t) return;
  ev.preventDefault();
  const botao = document.querySelector(`.tecla[data-t="${CSS.escape(t)}"]`);
  if (botao) { botao.classList.add("pressionada"); setTimeout(() => botao.classList.remove("pressionada"), 120); }
  tecla(t);
});

// Links diretos: ...#exemplos abre a aba de exemplos; ?explicacao=codigo abre o passo a passo no modo código
if (new URLSearchParams(location.search).get("explicacao") === "codigo") estado.explicacao = "cod";
pintarIcones();
montarPassos();
render();
if (location.hash) trocarAba(location.hash.slice(1));
iniciarPython();
