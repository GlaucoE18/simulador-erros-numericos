import math
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


def ajustar_precisao(valor: float, n: int, metodo: str) -> float:
    """Retorna o valor com n digitos significativos."""
    if valor == 0.0 or not math.isfinite(valor):
        return valor

    expoente = math.floor(math.log10(abs(valor)))
    escala = 10.0 ** (n - 1 - expoente)
    escalado = valor * escala

    if metodo == "Truncamento":
        ajustado = math.trunc(escalado)  # truncamento em direcao a zero
    else:
        # Arredondamento decimal simples, com empate afastando-se de zero.
        ajustado = math.floor(escalado + 0.5) if escalado >= 0 else math.ceil(escalado - 0.5)

    return ajustado / escala


def calcular(x: float, y: float, operacao: str) -> float:
    if operacao == "+":
        return x + y
    if operacao == "-":
        return x - y
    if operacao == "×":
        return x * y
    if operacao == "÷":
        if y == 0:
            raise ZeroDivisionError("A divisão por zero não é permitida.")
        return x / y
    raise ValueError("Operação inválida.")


def formatar(valor: float) -> str:
    if math.isnan(valor):
        return "Indefinido"
    if math.isinf(valor):
        return "Infinito" if valor > 0 else "-Infinito"
    return f"{valor:.12e}"


class SimuladorErrosApp:
    BG = "#0b1020"
    CARD = "#121a2d"
    CARD_INNER = "#0d1526"
    BORDER = "#283650"
    TEXT = "#e8edf7"
    MUTED = "#8b98b4"
    MINT = "#72e3c2"
    YELLOW = "#ffca78"

    def __init__(self, root):
        self.root = root
        self.root.title("Numerix | Simulador de Erros Numéricos")
        self.root.geometry("1050x780")
        self.root.minsize(900, 700)
        self.root.configure(bg=self.BG)

        self._configurar_estilos()
        self._montar_interface()

    def _configurar_estilos(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Dark.TCombobox",
            fieldbackground="#0b1222",
            background="#202c43",
            foreground=self.TEXT,
            arrowcolor=self.MINT,
            bordercolor=self.BORDER,
            padding=8,
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", "#0b1222")],
            foreground=[("readonly", self.TEXT)],
            selectbackground=[("readonly", "#0b1222")],
            selectforeground=[("readonly", self.TEXT)],
        )
        style.configure(
            "Dark.TSpinbox",
            fieldbackground="#0b1222",
            background="#202c43",
            foreground=self.TEXT,
            arrowcolor=self.MINT,
            bordercolor=self.BORDER,
            padding=7,
        )

    def _montar_interface(self):
        outer = tk.Frame(self.root, bg=self.BG, padx=26, pady=22)
        outer.pack(fill="both", expand=True)

        header = tk.Frame(outer, bg=self.BG)
        header.pack(fill="x", pady=(0, 18))

        tk.Label(
            header, text="NUMERIX", bg=self.BG, fg=self.MINT,
            font=("Segoe UI", 25, "bold")
        ).pack(anchor="w")
        tk.Label(
            header, text="SIMULADOR DE PROPAGAÇÃO DE ERROS NUMÉRICOS",
            bg=self.BG, fg=self.MUTED, font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(2, 0))

        body = tk.Frame(outer, bg=self.BG)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=4, uniform="col")
        body.columnconfigure(1, weight=6, uniform="col")
        body.rowconfigure(0, weight=1)

        left = self._card(body, "CONFIGURAR CÁLCULO")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 9))

        right = self._card(body, "RESULTADOS")
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 0))

        self.x_var = tk.StringVar(value="0.76545")
        self.y_var = tk.StringVar(value="0.76541")
        self.op_var = tk.StringVar(value="−  Subtração")
        self.digits_var = tk.IntVar(value=4)
        self.method_var = tk.StringVar(value="Arredondamento")
        self.limit_operands_var = tk.BooleanVar(value=True)

        self._label(left, "Valor x").pack(anchor="w", pady=(3, 5))
        self._entry(left, self.x_var).pack(fill="x", pady=(0, 12))
        self._label(left, "Valor y").pack(anchor="w", pady=(0, 5))
        self._entry(left, self.y_var).pack(fill="x", pady=(0, 12))

        self._label(left, "Operação").pack(anchor="w", pady=(0, 5))
        op_combo = ttk.Combobox(
            left, textvariable=self.op_var, state="readonly",
            values=["+  Soma", "−  Subtração", "×  Multiplicação", "÷  Divisão"],
            style="Dark.TCombobox"
        )
        op_combo.pack(fill="x", pady=(0, 12))

        self._label(left, "Dígitos significativos").pack(anchor="w", pady=(0, 5))
        spin = ttk.Spinbox(
            left, from_=1, to=15, textvariable=self.digits_var,
            state="readonly", style="Dark.TSpinbox"
        )
        spin.pack(fill="x", pady=(0, 12))

        self._label(left, "Método de precisão").pack(anchor="w", pady=(0, 5))
        method_combo = ttk.Combobox(
            left, textvariable=self.method_var, state="readonly",
            values=["Truncamento", "Arredondamento"],
            style="Dark.TCombobox"
        )
        method_combo.pack(fill="x", pady=(0, 10))

        check = tk.Checkbutton(
            left, text="Limitar também os operandos",
            variable=self.limit_operands_var, bg=self.CARD, fg=self.TEXT,
            activebackground=self.CARD, activeforeground=self.MINT,
            selectcolor="#0b1222", font=("Segoe UI", 9),
            anchor="w", wraplength=300
        )
        check.pack(fill="x", pady=(0, 14))

        self._button(left, "CALCULAR RESULTADO", self.executar_calculo, primary=True).pack(fill="x", pady=(0, 9))
        self._label(left, "TESTES RÁPIDOS", color=self.MUTED, size=9, bold=True).pack(anchor="w", pady=(10, 7))
        self._button(left, "Cancelamento subtrativo", self.teste_cancelamento).pack(fill="x", pady=(0, 8))
        self._button(left, "10 somas sucessivas", self.teste_somas).pack(fill="x", pady=(0, 8))
        self._button(left, "Limpar / novo cálculo", self.limpar).pack(fill="x", pady=(0, 2))

        tk.Label(
            right, text="Comparação entre a referência e a simulação",
            bg=self.CARD, fg=self.MUTED, font=("Segoe UI", 9)
        ).pack(anchor="w", padx=18, pady=(2, 12))

        self.result_labels = {}
        results = [
            ("exato", "VALOR DE REFERÊNCIA", self.TEXT),
            ("aproximado", "VALOR APROXIMADO", self.MINT),
            ("absoluto", "ERRO ABSOLUTO", self.YELLOW),
            ("relativo", "ERRO RELATIVO", self.YELLOW),
            ("percentual", "ERRO RELATIVO (%)", self.TEXT),
        ]
        for key, title, color in results:
            box = tk.Frame(right, bg=self.CARD_INNER, highlightbackground=self.BORDER, highlightthickness=1)
            box.pack(fill="x", padx=2, pady=5)
            tk.Label(
                box, text=title, bg=self.CARD_INNER, fg=self.MUTED,
                font=("Segoe UI", 8, "bold")
            ).pack(anchor="w", padx=12, pady=(8, 2))
            value = tk.Label(
                box, text="—", bg=self.CARD_INNER, fg=color,
                font=("Consolas", 12, "bold"), anchor="w"
            )
            value.pack(fill="x", padx=12, pady=(0, 9))
            self.result_labels[key] = value

        tk.Label(
            right, text="DETALHES DA SIMULAÇÃO", bg=self.CARD, fg=self.MUTED,
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=2, pady=(13, 7))

        self.details = tk.Text(
            right, height=8, wrap="word", bg=self.CARD_INNER, fg="#c2cce0",
            insertbackground=self.MINT, relief="flat", padx=12, pady=10,
            font=("Consolas", 9), highlightbackground=self.BORDER,
            highlightthickness=1
        )
        self.details.pack(fill="both", expand=True, padx=2)
        self._set_details(
            "Configure os valores e clique em Calcular resultado.\n\n"
            "Dica: o teste de cancelamento usa 0.76545 − 0.76541 "
            "com 4 dígitos significativos."
        )

        tk.Label(
            outer, text="CÁLCULO NUMÉRICO  /  ARITMÉTICA DE PRECISÃO LIMITADA",
            bg=self.BG, fg=self.MUTED, font=("Segoe UI", 8)
        ).pack(anchor="w", pady=(14, 0))

    def _card(self, parent, title):
        card = tk.Frame(parent, bg=self.CARD, highlightbackground=self.BORDER, highlightthickness=1, padx=18, pady=17)
        tk.Label(
            card, text=title, bg=self.CARD, fg=self.MINT,
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", pady=(0, 16))
        return card

    def _label(self, parent, text, color=None, size=9, bold=False):
        return tk.Label(
            parent, text=text, bg=self.CARD, fg=color or self.TEXT,
            font=("Segoe UI", size, "bold" if bold else "normal")
        )

    def _entry(self, parent, variable):
        return tk.Entry(
            parent, textvariable=variable, bg="#0b1222", fg=self.TEXT,
            insertbackground=self.MINT, relief="flat", font=("Consolas", 11),
            highlightthickness=1, highlightbackground=self.BORDER,
            highlightcolor=self.MINT
        )

    def _button(self, parent, text, command, primary=False):
        bg = self.MINT if primary else "#202c43"
        fg = "#071a1a" if primary else self.TEXT
        active = "#8af0d4" if primary else "#2d3e5e"
        return tk.Button(
            parent, text=text, command=command, bg=bg, fg=fg,
            activebackground=active, activeforeground=fg,
            relief="flat", cursor="hand2", font=("Segoe UI", 9, "bold"),
            padx=10, pady=10, bd=0
        )

    def _set_details(self, text):
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", text)
        self.details.configure(state="disabled")

    def _ler_valores(self):
        try:
            x = float(self.x_var.get().strip().replace(",", "."))
            y = float(self.y_var.get().strip().replace(",", "."))
            n = int(self.digits_var.get())
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError
            if not 1 <= n <= 15:
                raise ValueError
            return x, y, n
        except (ValueError, tk.TclError):
            messagebox.showerror(
                "Entrada inválida",
                "Digite números válidos para x e y e escolha de 1 a 15 dígitos significativos."
            )
            return None

    def _operacao(self):
        texto = self.op_var.get()
        if texto.startswith("+"):
            return "+"
        if texto.startswith("−"):
            return "-"
        if texto.startswith("×"):
            return "×"
        return "÷"

    def _mostrar_resultados(self, exato, aproximado, detalhes):
        ea = abs(exato - aproximado)
        self.result_labels["exato"].configure(text=formatar(exato))
        self.result_labels["aproximado"].configure(text=formatar(aproximado))
        self.result_labels["absoluto"].configure(text=formatar(ea))

        if aproximado == 0:
            self.result_labels["relativo"].configure(text="Indefinido (aproximação = 0)")
            self.result_labels["percentual"].configure(text="Indefinido")
        else:
            er = ea / abs(aproximado)
            self.result_labels["relativo"].configure(text=formatar(er))
            self.result_labels["percentual"].configure(text=formatar(er * 100) + " %")

        self._set_details(detalhes)

    def executar_calculo(self):
        dados = self._ler_valores()
        if dados is None:
            return
        x, y, n = dados
        metodo = self.method_var.get()
        op = self._operacao()

        try:
            exato = calcular(x, y, op)
            xm, ym = x, y
            linhas = [
                f"Método: {metodo}",
                f"Dígitos significativos: {n}",
                f"Operação: {x} {op} {y}",
            ]
            if self.limit_operands_var.get():
                xm = ajustar_precisao(x, n, metodo)
                ym = ajustar_precisao(y, n, metodo)
                linhas.extend([
                    "",
                    "Operandos representados na máquina:",
                    f"x_maquina = {formatar(xm)}",
                    f"y_maquina = {formatar(ym)}",
                ])
            intermediario = calcular(xm, ym, op)
            aproximado = ajustar_precisao(intermediario, n, metodo)
            linhas.extend([
                "",
                f"Resultado intermediário: {formatar(intermediario)}",
                f"Resultado ajustado para {n} dígitos significativos.",
                "",
                "Erro absoluto = |referência − aproximado|",
                "Erro relativo = erro absoluto / |aproximado|",
            ])
            self._mostrar_resultados(exato, aproximado, "\n".join(linhas))
        except (ZeroDivisionError, OverflowError, ValueError) as exc:
            messagebox.showerror("Não foi possível calcular", str(exc))

    def teste_cancelamento(self):
        self.x_var.set("0.76545")
        self.y_var.set("0.76541")
        self.op_var.set("−  Subtração")
        self.digits_var.set(4)
        self.method_var.set("Arredondamento")
        self.limit_operands_var.set(True)
        self.executar_calculo()

    def teste_somas(self):
        try:
            valor = float(self.x_var.get().strip().replace(",", "."))
            if not math.isfinite(valor):
                raise ValueError
        except ValueError:
            messagebox.showerror("Entrada inválida", "Digite um número válido no campo Valor x.")
            return

        quantidade = simpledialog.askinteger(
            "Somas sucessivas",
            "Quantas vezes deseja somar o valor de x?",
            initialvalue=10, minvalue=1, maxvalue=100000, parent=self.root
        )
        if quantidade is None:
            return

        n = int(self.digits_var.get())
        metodo = self.method_var.get()
        parcela = ajustar_precisao(valor, n, metodo) if self.limit_operands_var.get() else valor
        acumulado = 0.0
        for _ in range(quantidade):
            acumulado = ajustar_precisao(acumulado + parcela, n, metodo)

        referencia = valor * quantidade
        detalhes = (
            "TESTE DE PROPAGAÇÃO: SOMAS SUCESSIVAS\n"
            f"Valor somado: {formatar(valor)}\n"
            f"Quantidade de somas: {quantidade}\n"
            f"Método: {metodo}\n"
            f"Dígitos significativos: {n}\n"
            f"Valor usado em cada etapa: {formatar(parcela)}\n\n"
            "Após cada soma, o acumulado é ajustado para a precisão escolhida."
        )
        self._mostrar_resultados(referencia, acumulado, detalhes)

    def limpar(self):
        self.x_var.set("")
        self.y_var.set("")
        self.op_var.set("+  Soma")
        self.digits_var.set(4)
        self.method_var.set("Truncamento")
        self.limit_operands_var.set(True)
        for label in self.result_labels.values():
            label.configure(text="—")
        self._set_details("Campos limpos. Digite novos valores para iniciar outro cálculo.")


if __name__ == "__main__":
    root = tk.Tk()
    app = SimuladorErrosApp(root)
    root.mainloop()
