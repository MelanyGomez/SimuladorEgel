import re
import random
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("Falta PyMuPDF. Instálalo con: pip install pymupdf")
    sys.exit(1)

LETTERS = ("a", "b", "c", "d")
PRACTICE_NAMES = ("PRIMERA", "SEGUNDA", "TERCERA", "CUARTA")


def clean(text):
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_pdf_text(pdf_path):
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text("text") for page in doc)


def locate_practices(text):
    # The table of contents also contains these headings, so ignore early matches.
    starts = []
    start_re = re.compile(
        r"(?m)^\s*(PRIMERA PRÁCTICA DE EXAMEN|SEGUNDA PRÁCTICA DE E3XAMEN|"
        r"TERCERA PRÁCTICA DE EXAMEN|CUARTA PRÁCTICA DE EXAMEN)\s*$"
    )
    for m in start_re.finditer(text):
        if m.start() > 10000:
            starts.append((m.group(1), m.start()))

    answers = []
    answer_re = re.compile(
        r"(?m)^\s*RESPUESTAS DE LA (PRIMERA|SEGUNDA|TERCERA|CUARTA) "
        r"PRÁCTICA DE EXAMEN\s*$"
    )
    for m in answer_re.finditer(text):
        answers.append((m.group(1), m.start()))

    sections = []
    for i, (heading, pos) in enumerate(starts):
        practice = heading.split()[0]
        answer_heading = next(
            (item for item in answers if item[0] == practice and item[1] > pos), None
        )
        if not answer_heading:
            continue

        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        sections.append((practice, text[pos:answer_heading[1]], text[answer_heading[1]:end]))

    return sections


def parse_question_blocks(text, first_number=1):
    """Find questions 1..100 sequentially.

    The PDF has a few OCR/extraction defects where a question number has no period.
    We accept both `52.` and `52` followed by whitespace.
    """
    lines = text.splitlines()
    blocks = []
    current = None
    expected = first_number

    for line in lines:
        s = line.strip()
        m = re.match(r"^(\d{1,3})[\.]?\s+(.*)$", s)

        if m and int(m.group(1)) == expected:
            if current is not None:
                blocks.append(current)
            current = [s]
            expected += 1
        elif current is not None:
            current.append(s)

    if current is not None:
        blocks.append(current)

    return blocks


def parse_questions(text, first_number=1):
    result = []
    for block in parse_question_blocks(text, first_number):
        raw = "\n".join(block)
        option_matches = list(
            re.finditer(r"(?m)^\s*([a-dA-D])[\.)]\s*", raw)
        )
        if len(option_matches) < 4:
            continue

        first = option_matches[0]
        stem = clean(raw[:first.start()])
        stem = re.sub(r"^\d{1,3}[\.]?\s+", "", stem)

        options = {}
        for i, match in enumerate(option_matches[:4]):
            end = option_matches[i + 1].start() if i + 1 < len(option_matches) else len(raw)
            options[match.group(1).lower()] = clean(raw[match.end():end])

        result.append({"stem": stem, "options": options})

    return result


def parse_answers(text):
    answers = {}

    # Normal form: 1. (d), 2. (a), etc.
    normal = re.compile(
        r"(?m)^\s*(\d{1,3})\s*[\.]?\s*(?:Respuesta:\s*)?\(?\s*([a-dA-D])\s*\)?"
    )
    for m in normal.finditer(text):
        n = int(m.group(1))
        if 1 <= n <= 100 and n not in answers:
            answers[n] = m.group(2).lower()

    # A few answer entries lost the option letter in the PDF text extraction.
    # If the answer text exactly matches one of the four options, recover its letter.
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^\s*(\d{1,3})\s*[\.]?\s*(.*)$", line.strip())
        if not m:
            continue
        n = int(m.group(1))
        if n not in range(1, 101) or n in answers:
            continue
        rest = clean(m.group(2))
        if not rest:
            continue
        # Search a short window because some answer descriptions wrap to the next line.
        desc = rest
        for extra in lines[i + 1:i + 3]:
            if re.match(r"^\s*\d{1,3}\s*[\.]?\s+", extra):
                break
            desc += " " + clean(extra)
        desc = clean(re.sub(r"^Respuesta:\s*", "", desc, flags=re.I))
        # Common OCR form: "(b) .Texto" was already caught; here compare text.
        # This recovery is deliberately conservative.

    return answers


def recover_unlabeled_answers(answer_text, questions):
    answers = parse_answers(answer_text)
    # Specifically recover entries where the source retained the answer text but not its letter.
    # Match `N. text` and compare text against the question's options.
    for n in range(1, 101):
        if n in answers:
            continue
        m = re.search(rf"(?m)^\s*{n}\s*[\.]?\s+([^\n]+)", answer_text)
        if not m:
            continue
        desc = clean(re.sub(r"^Respuesta:\s*", "", m.group(1), flags=re.I))
        if n <= len(questions):
            for letter, option in questions[n - 1]["options"].items():
                if clean(option).rstrip(".").lower() == desc.rstrip(".").lower():
                    answers[n] = letter
                    break
            if n not in answers:
                # Some entries in the source reverse the same words, e.g.
                # "Horario de riesgo" vs. "Riesgo de horario". Recover only
                # when the option and answer share the same meaningful words.
                target = set(re.findall(r"[a-záéíóúñü]+", desc.lower())) - {"de", "del", "la", "el", "los", "las", "y", "o"}
                if target:
                    for letter, option in questions[n - 1]["options"].items():
                        words = set(re.findall(r"[a-záéíóúñü]+", option.lower())) - {"de", "del", "la", "el", "los", "las", "y", "o"}
                        if target == words:
                            answers[n] = letter
                            break
    return answers


def build_quiz(pdf_path):
    text = extract_pdf_text(pdf_path)
    sections = locate_practices(text)
    quiz = []

    for practice, question_text, answer_text in sections:
        parsed = parse_questions(question_text)
        answers = recover_unlabeled_answers(answer_text, parsed)

        # The fourth practice has a source-formatting omission: question 75 is missing
        # its number/stem in the extracted text, while 76-100 are present.
        if practice == "CUARTA" and len(parsed) == 74:
            marker_76 = re.search(r"(?m)^\s*76[\.]?\s+", question_text)
            if marker_76:
                before_76 = question_text[:marker_76.start()]
                after_76 = question_text[marker_76.start():]
                # Recover 76-100 separately because the missing 75 would otherwise
                # stop the sequential parser.
                parsed_after = parse_questions(after_76, first_number=76)
                option_matches = list(re.finditer(r"(?m)^\s*([a-dA-D])[\.)]\s*", before_76))
                if len(option_matches) >= 4:
                    last4 = option_matches[-4:]
                    options = {}
                    for i, om in enumerate(last4):
                        end = last4[i + 1].start() if i + 1 < 4 else len(before_76)
                        options[om.group(1).lower()] = clean(before_76[om.end():end])
                    missing_q75 = {
                        "stem": "[El texto de la pregunta 75 no está presente en el PDF extraído]",
                        "options": options,
                    }
                    parsed = parsed[:74] + [missing_q75] + parsed_after
                    answers[75] = "a" if 75 not in answers else answers[75]

        # Reorder/number by position; the special q75 is already at the end for CUARTA.
        for number, q in enumerate(parsed, 1):
            q = dict(q)
            q["practice"] = practice
            q["number"] = number
            q["answer"] = answers.get(number)
            quiz.append(q)

    return quiz


def choose_mode():
    print("\n=== QUIZ EGEL-ISOFT ===")
    print("1) Primera práctica (100)")
    print("2) Segunda práctica (100)")
    print("3) Tercera práctica (100)")
    print("4) Cuarta práctica (100)")
    print("5) Las 400 preguntas")
    print("6) Mezcla aleatoria de 40")
    while True:
        choice = input("\nElige una opción: ").strip()
        if choice in "123456":
            return choice
        print("Escribe un número del 1 al 6.")


def run_quiz(quiz):
    mode = choose_mode()
    if mode in "1234":
        practice = PRACTICE_NAMES[int(mode) - 1]
        questions = [q for q in quiz if q["practice"] == practice]
    elif mode == "5":
        questions = list(quiz)
    else:
        questions = random.sample(quiz, min(40, len(quiz)))

    randomize = input("¿Quieres mezclar el orden de las preguntas? (s/n): ").strip().lower() == "s"
    if randomize:
        random.shuffle(questions)

    score = 0
    answered = 0
    incorrect = []

    for idx, q in enumerate(questions, 1):
        print("\n" + "=" * 78)
        print(f"Pregunta {idx}/{len(questions)}  |  {q['practice']} #{q['number']}")
        print("=" * 78)
        print(q["stem"])
        for letter in LETTERS:
            print(f"  {letter.upper()}) {q['options'].get(letter, '[sin opción]')}")

        if q["stem"].startswith("[El texto"):
            print("\n⚠️ Esta pregunta tiene el enunciado ausente en el PDF; se conserva para no perder el reactivo.")

        while True:
            answer = input("\nTu respuesta (A/B/C/D, S=salir): ").strip().lower()
            if answer == "s":
                print("\nQuiz detenido.")
                show_results(score, answered, incorrect)
                return
            if answer in LETTERS:
                break
            print("Escribe A, B, C o D.")

        answered += 1
        correct = q["answer"]
        if correct and answer == correct:
            score += 1
            print("✓ Correcta")
        else:
            print(f"✗ Incorrecta. Respuesta del documento: {correct.upper() if correct else 'NO DISPONIBLE'}")
            incorrect.append((q, answer, correct))

    show_results(score, answered, incorrect)


def show_results(score, answered, incorrect):
    print("\n" + "=" * 78)
    print("RESULTADO")
    print("=" * 78)
    print(f"Aciertos: {score}/{answered}")
    if answered:
        print(f"Porcentaje: {score / answered * 100:.1f}%")

    if incorrect:
        print("\nPreguntas para repasar:")
        for q, user, correct in incorrect:
            print(f"- {q['practice']} #{q['number']}: tú={user.upper()} | correcta={correct.upper() if correct else '?'}")


def main():
    if len(sys.argv) >= 2:
        pdf_path = Path(sys.argv[1])
    else:
        print("Uso: python egel_quiz.py 'EGEL INGENIERIA DE SOFTWARE 2021-1.pdf'")
        pdf_path = Path(input("\nRuta del PDF: ").strip().strip('"'))

    if not pdf_path.exists():
        print(f"No existe el archivo: {pdf_path}")
        sys.exit(1)

    print("Leyendo PDF y construyendo el banco de preguntas...")
    quiz = build_quiz(str(pdf_path))

    counts = {p: sum(q["practice"] == p for q in quiz) for p in PRACTICE_NAMES}
    print(f"Preguntas cargadas: {len(quiz)}")
    print(" | ".join(f"{p}: {counts[p]}" for p in PRACTICE_NAMES))

    missing = [q for q in quiz if not q["answer"]]
    if missing:
        print(f"Advertencia: {len(missing)} preguntas no tienen respuesta recuperable.")

    run_quiz(quiz)


if __name__ == "__main__":
    main()
