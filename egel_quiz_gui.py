import random
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

from egel_quiz import build_quiz


# Paleta azul suave para favorecer una interfaz limpia y tranquila.
BG = "#EAF3FB"
CARD = "#FFFFFF"
BLUE = "#1F5F8B"
BLUE_DARK = "#174A6B"
BLUE_LIGHT = "#D7EAF7"
TEXT = "#17324D"
MUTED = "#5F7180"
GREEN = "#2E7D5B"
RED = "#B94A48"
WHITE = "#FFFFFF"


class QuizApp(tk.Tk):
    def __init__(self, quiz):
        super().__init__()
        self.title("Quiz EGEL-ISOFT — 400 preguntas")
        self.geometry("1050x760")
        self.minsize(850, 650)
        self.quiz = quiz
        self.questions = []
        self.index = 0
        self.score = 0
        self.answered = 0
        self.wrong = []
        self.section_score = 0
        self.section_answered = 0
        self.section_wrong = []
        self.section_name = None
        self.selected = tk.StringVar(value="")
        self.feedback = tk.StringVar(value="")
        self.answer_buttons = []
        self.next_button = None
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.configure(bg=BG)
        self.show_setup()

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def make_button(self, parent, text, command, primary=True, **kwargs):
        options = {
            "font": ("Segoe UI", 10, "bold"),
            "cursor": "hand2",
            "bd": 0,
            "relief": "flat",
            "padx": 18,
            "pady": 10,
        }
        if primary:
            options.update(bg=BLUE, fg=WHITE, activebackground=BLUE_DARK, activeforeground=WHITE)
        else:
            options.update(bg=BLUE_LIGHT, fg=BLUE_DARK, activebackground="#C4DFEF", activeforeground=BLUE_DARK)
        options.update(kwargs)
        return tk.Button(parent, text=text, command=command, **options)

    def show_setup(self):
        self.clear()
        self.configure(bg=BG)

        header = tk.Frame(self, bg=BLUE, height=105)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header, text="Quiz EGEL-ISOFT", bg=BLUE, fg=WHITE,
            font=("Segoe UI", 25, "bold")
        ).pack(pady=(20, 2))
        tk.Label(
            header, text="Practica con las 400 preguntas del documento",
            bg=BLUE, fg="#E8F4FC", font=("Segoe UI", 11)
        ).pack()

        card = tk.Frame(self, bg=CARD, bd=0, highlightthickness=1, highlightbackground="#C8DDEA")
        card.pack(fill="x", padx=110, pady=35)

        tk.Label(card, text="¿Cómo quieres practicar?", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=30, pady=(25, 15))

        self.mode = tk.StringVar(value="PRIMERA")
        modes = [
            ("PRIMERA — 100 preguntas", "PRIMERA"),
            ("SEGUNDA — 100 preguntas", "SEGUNDA"),
            ("TERCERA — 100 preguntas", "TERCERA"),
            ("CUARTA — 100 preguntas", "CUARTA"),
            ("TODAS — 400 preguntas", "TODAS"),
            ("ALEATORIO — 40 preguntas", "ALEATORIO"),
        ]
        for text, value in modes:
            tk.Radiobutton(
                card, text=text, variable=self.mode, value=value,
                bg=CARD, fg=TEXT, activebackground=CARD, activeforeground=BLUE,
                selectcolor=BLUE_LIGHT, font=("Segoe UI", 10),
            ).pack(anchor="w", padx=40, pady=3)

        self.shuffle = tk.BooleanVar(value=False)
        tk.Checkbutton(
            card, text="Mezclar el orden de las preguntas", variable=self.shuffle,
            bg=CARD, fg=TEXT, activebackground=CARD, activeforeground=BLUE,
            selectcolor=BLUE_LIGHT, font=("Segoe UI", 10),
        ).pack(anchor="w", padx=40, pady=(18, 8))

        self.make_button(card, "Comenzar quiz", self.start).pack(anchor="w", padx=40, pady=(5, 28))

        tk.Label(
            self, text="Después de responder podrás ver si acertaste. Al terminar una sección verás tu resumen y podrás revisar tus errores.",
            bg=BG, fg=MUTED, font=("Segoe UI", 9), wraplength=800, justify="center"
        ).pack(pady=5)

    def start(self):
        mode = self.mode.get()

        if mode == "TODAS":
            # Se conservan las 4 prácticas en orden para poder mostrar
            # un resumen independiente al terminar cada una.
            questions = []
            for practice in ("PRIMERA", "SEGUNDA", "TERCERA", "CUARTA"):
                section = [q for q in self.quiz if q["practice"] == practice]
                if self.shuffle.get():
                    random.shuffle(section)
                questions.extend(section)
        elif mode == "ALEATORIO":
            questions = random.sample(self.quiz, min(40, len(self.quiz)))
            if self.shuffle.get():
                random.shuffle(questions)
        else:
            questions = [q for q in self.quiz if q["practice"] == mode]
            if self.shuffle.get():
                random.shuffle(questions)

        self.questions = questions
        self.index = 0
        self.score = 0
        self.answered = 0
        self.wrong = []
        self.section_score = 0
        self.section_answered = 0
        self.section_wrong = []
        self.section_name = self.questions[0]["practice"] if self.questions else None
        self.show_question()

    def show_question(self):
        self.clear()
        self.configure(bg=BG)
        q = self.questions[self.index]
        self.selected.set("")
        self.feedback.set("")
        self.answer_buttons = []

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=30, pady=(18, 0))
        tk.Label(
            top, text=f"Pregunta {self.index + 1} de {len(self.questions)}",
            bg=BG, fg=TEXT, font=("Segoe UI", 12, "bold")
        ).pack(side="left")
        tk.Label(
            top, text=f"{q['practice']} #{q['number']}",
            bg=BG, fg=BLUE, font=("Segoe UI", 10, "bold")
        ).pack(side="right")

        progress = tk.Canvas(self, height=9, bg="#D5E3EC", highlightthickness=0)
        progress.pack(fill="x", padx=30, pady=(8, 22))
        width = max(1, int(progress.winfo_reqwidth() * ((self.index + 1) / len(self.questions))))
        # Canvas width se calcula mejor después de actualizar la ventana.
        self.update_idletasks()
        width = max(1, int(progress.winfo_width() * ((self.index + 1) / len(self.questions))))
        progress.create_rectangle(0, 0, width, 9, fill=BLUE, outline=BLUE)

        card = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground="#C8DDEA")
        card.pack(fill="both", expand=True, padx=30, pady=(0, 10))

        stem = q["stem"]
        tk.Label(
            card, text=stem, wraplength=900, justify="left", anchor="w",
            bg=CARD, fg=TEXT, font=("Segoe UI", 14, "bold")
        ).pack(fill="x", padx=30, pady=(28, 20))

        options = tk.Frame(card, bg=CARD)
        options.pack(fill="x", padx=35)
        for letter in "abcd":
            text = q["options"].get(letter, "[sin opción]")
            rb = tk.Radiobutton(
                options, text=f"{letter.upper()}) {text}",
                variable=self.selected, value=letter,
                bg=CARD, fg=TEXT, activebackground=CARD, activeforeground=BLUE,
                selectcolor=BLUE_LIGHT, font=("Segoe UI", 11),
                wraplength=850, justify="left", anchor="w",
            )
            rb.pack(fill="x", anchor="w", pady=7)
            self.answer_buttons.append(rb)

        tk.Label(
            card, textvariable=self.feedback, wraplength=850, justify="left",
            bg=CARD, fg=TEXT, font=("Segoe UI", 11, "bold")
        ).pack(fill="x", padx=35, pady=(15, 5))

        self.next_button = self.make_button(card, "Comprobar respuesta", self.check_answer)
        self.next_button.pack(pady=(5, 15))

        self.make_button(self, "Salir al menú", self.show_setup, primary=False, padx=12, pady=7).pack(pady=(0, 8))

    def check_answer(self):
        answer = self.selected.get()
        if not answer:
            messagebox.showwarning("Falta responder", "Selecciona A, B, C o D.")
            return

        q = self.questions[self.index]
        correct = q["answer"]
        self.answered += 1
        self.section_answered += 1

        for rb in self.answer_buttons:
            rb.configure(state="disabled")

        if answer == correct:
            self.score += 1
            self.section_score += 1
            self.feedback.set("✓ Correcta — ¡muy bien!")
            self.feedback_label_color(GREEN)
        else:
            item = (q, answer, correct)
            self.wrong.append(item)
            self.section_wrong.append(item)
            self.feedback.set(
                f"✗ Incorrecta. Elegiste {answer.upper()} y la respuesta correcta es {correct.upper()}."
            )
            self.feedback_label_color(RED)

        last_question = self.index + 1 >= len(self.questions)
        practice_changes = (
            not last_question and self.questions[self.index + 1]["practice"] != q["practice"]
        )

        if practice_changes:
            self.next_button.configure(text="Ver resumen de la sección", command=self.next_question)
        elif last_question:
            self.next_button.configure(text="Ver resultado", command=self.next_question)
        else:
            self.next_button.configure(text="Siguiente", command=self.next_question)

    def feedback_label_color(self, color):
        # El Label con StringVar se busca de forma sencilla entre los hijos de la tarjeta.
        for widget in self.winfo_children():
            pass
        # Cambiamos el color de todos los labels que usan el texto de feedback.
        def walk(parent):
            for child in parent.winfo_children():
                if isinstance(child, tk.Label) and child.cget("textvariable") == str(self.feedback):
                    child.configure(fg=color)
                walk(child)
        walk(self)

    def next_question(self):
        q = self.questions[self.index]
        last_question = self.index + 1 >= len(self.questions)
        practice_changes = (
            not last_question and self.questions[self.index + 1]["practice"] != q["practice"]
        )

        if practice_changes:
            self.show_section_result(q["practice"], final=False)
            return

        if last_question:
            self.show_result()
            return

        self.index += 1
        self.show_question()

    def show_section_result(self, practice, final=False):
        self.clear()
        self.configure(bg=BG)
        total = self.section_answered
        incorrect = total - self.section_score
        pct = self.section_score / total * 100 if total else 0

        header = tk.Frame(self, bg=BLUE)
        header.pack(fill="x")
        tk.Label(header, text=f"Resumen — {practice}", bg=BLUE, fg=WHITE,
                 font=("Segoe UI", 23, "bold")).pack(pady=(22, 4))
        tk.Label(header, text="Terminaste esta sección", bg=BLUE, fg="#E8F4FC",
                 font=("Segoe UI", 11)).pack(pady=(0, 18))

        stats = tk.Frame(self, bg=BG)
        stats.pack(fill="x", padx=70, pady=25)
        self.stat_card(stats, "CORRECTAS", str(self.section_score), GREEN, 0)
        self.stat_card(stats, "INCORRECTAS", str(incorrect), RED, 1)
        self.stat_card(stats, "PORCENTAJE", f"{pct:.1f}%", BLUE, 2)

        self.review_frame = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground="#C8DDEA")
        self.review_frame.pack(fill="both", expand=True, padx=55, pady=(0, 15))
        self.build_review(self.review_frame, self.section_wrong)

        if final:
            button_text = "Volver al menú"
            command = self.show_setup
        else:
            button_text = "Continuar con la siguiente sección"
            command = self.continue_after_section
        self.make_button(self, button_text, command).pack(pady=(0, 18))

    def stat_card(self, parent, title, value, color, column):
        card = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground="#C8DDEA")
        card.grid(row=0, column=column, sticky="nsew", padx=7)
        parent.grid_columnconfigure(column, weight=1)
        tk.Label(card, text=title, bg=CARD, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(pady=(15, 2))
        tk.Label(card, text=value, bg=CARD, fg=color,
                 font=("Segoe UI", 25, "bold")).pack(pady=(0, 15))

    def build_review(self, parent, wrong):
        tk.Label(parent, text="Revisión de respuestas incorrectas", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=20, pady=(15, 5))

        if not wrong:
            tk.Label(parent, text="🎉 No hubo respuestas incorrectas en esta sección.",
                     bg=CARD, fg=GREEN, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=20, pady=15)
            return

        container = tk.Frame(parent, bg=CARD)
        container.pack(fill="both", expand=True, padx=15, pady=5)
        scrollbar = tk.Scrollbar(container)
        scrollbar.pack(side="right", fill="y")
        text = tk.Text(container, wrap="word", yscrollcommand=scrollbar.set,
                       bg="#F8FBFD", fg=TEXT, relief="flat", bd=0,
                       font=("Segoe UI", 10), padx=12, pady=10)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text.yview)

        for i, (q, user, correct) in enumerate(wrong, 1):
            text.insert("end", f"{i}. {q['practice']} #{q['number']}\n", "title")
            text.insert("end", f"Pregunta: {q['stem']}\n")
            text.insert("end", f"Tu respuesta: {user.upper()}) {q['options'].get(user, '[sin opción]')}\n", "wrong")
            text.insert("end", f"Respuesta correcta: {correct.upper()}) {q['options'].get(correct, '[sin opción]')}\n", "correct")
            text.insert("end", "\n" + "─" * 85 + "\n\n")

        text.tag_configure("title", font=("Segoe UI", 10, "bold"), foreground=BLUE_DARK)
        text.tag_configure("wrong", foreground=RED)
        text.tag_configure("correct", foreground=GREEN)
        text.configure(state="disabled")

    def continue_after_section(self):
        # Avanza a la primera pregunta de la siguiente práctica y reinicia
        # únicamente los contadores de la sección.
        self.index += 1
        self.section_name = self.questions[self.index]["practice"]
        self.section_score = 0
        self.section_answered = 0
        self.section_wrong = []
        self.show_question()

    def show_result(self):
        self.clear()
        self.configure(bg=BG)
        pct = self.score / self.answered * 100 if self.answered else 0
        incorrect = self.answered - self.score

        header = tk.Frame(self, bg=BLUE)
        header.pack(fill="x")
        tk.Label(header, text="Resultado final", bg=BLUE, fg=WHITE,
                 font=("Segoe UI", 24, "bold")).pack(pady=(22, 4))
        tk.Label(header, text="Así quedó tu intento", bg=BLUE, fg="#E8F4FC",
                 font=("Segoe UI", 11)).pack(pady=(0, 18))

        stats = tk.Frame(self, bg=BG)
        stats.pack(fill="x", padx=70, pady=25)
        self.stat_card(stats, "CORRECTAS", str(self.score), GREEN, 0)
        self.stat_card(stats, "INCORRECTAS", str(incorrect), RED, 1)
        self.stat_card(stats, "PORCENTAJE", f"{pct:.1f}%", BLUE, 2)

        card = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground="#C8DDEA")
        card.pack(fill="both", expand=True, padx=55, pady=(0, 15))
        self.build_review(card, self.wrong)

        self.make_button(self, "Volver al menú", self.show_setup).pack(pady=(0, 18))


def choose_pdf():
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="Selecciona el PDF del EGEL",
        filetypes=[("PDF", "*.pdf")]
    )
    root.destroy()
    return Path(path) if path else None


def main():
    pdf = choose_pdf()
    if not pdf or not pdf.exists():
        return
    try:
        quiz = build_quiz(str(pdf))
    except Exception as exc:
        messagebox.showerror("Error al leer el PDF", f"No se pudo procesar el documento.\n\n{exc}")
        return

    if len(quiz) != 400:
        messagebox.showwarning(
            "Aviso",
            f"Se detectaron {len(quiz)} preguntas. El documento debería contener 400."
        )
    app = QuizApp(quiz)
    app.mainloop()


if __name__ == "__main__":
    main()
