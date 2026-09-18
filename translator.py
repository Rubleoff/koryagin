from __future__ import annotations

import re
import tkinter as tk
import unicodedata
from dataclasses import dataclass
from tkinter import messagebox, ttk


UNITS = {
    0: "zéro",
    1: "un",
    2: "deux",
    3: "trois",
    4: "quatre",
    5: "cinq",
    6: "six",
    7: "sept",
    8: "huit",
    9: "neuf",
}

TEENS = {
    10: "dix",
    11: "onze",
    12: "douze",
    13: "treize",
    14: "quatorze",
    15: "quinze",
    16: "seize",
    17: "dix sept",
    18: "dix huit",
    19: "dix neuf",
}

TENS = {
    20: "vingt",
    30: "trente",
    40: "quarante",
    50: "cinquante",
    60: "soixante",
}


# ============================================================
# ОШИБКИ
# ============================================================

@dataclass(frozen=True)
class NumberInputError(ValueError):
    message: str

    def __str__(self) -> str:
        return self.message


# ============================================================
# УЗЕЛ ДЕРЕВА РАЗБОРА
# ============================================================

@dataclass(frozen=True)
class TreeNode:
    """
    Один узел синтаксического дерева.

    label    — подпись узла;
    children — дочерние элементы.
    """

    label: str
    children: tuple["TreeNode", ...] = ()


def terminal(word: str) -> TreeNode:
    """
    Создаёт терминальный узел дерева.

    Терминалы записываем в кавычках,
    как в формальном описании языка.
    """
    return TreeNode(f'«{word}»')


# ============================================================
# НОРМАЛИЗАЦИЯ
# ============================================================

def normalise_key(text: str) -> str:
    """
    Приводит ввод к единому виду:
    - убирает лишние пробелы;
    - делает буквы строчными;
    - дефисы превращает в пробелы;
    - убирает акценты: zéro -> zero.
    """

    text = text.strip().lower()
    text = text.replace("’", "'").replace("œ", "oe")

    text = unicodedata.normalize("NFD", text)
    text = "".join(
        char
        for char in text
        if unicodedata.category(char) != "Mn"
    )

    text = re.sub(r"[-']", " ", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# ФОРМИРОВАНИЕ ФРАНЦУЗСКИХ ЧИСЕЛ
# ============================================================

def under_100_forms(number: int) -> list[str]:
    """
    Возвращает корректные французские формы числа от 0 до 99.

    Дефисы специально не используются:
    они будут обработаны нормализацией.
    """

    if not 0 <= number <= 99:
        raise ValueError("number должен быть в диапазоне 0..99")

    if number < 10:
        return [UNITS[number]]

    if 10 <= number <= 19:
        return [TEENS[number]]

    if 20 <= number <= 69:
        tens_part = number // 10 * 10
        units_part = number % 10

        tens_word = TENS[tens_part]

        if units_part == 0:
            return [tens_word]

        if units_part == 1:
            return [f"{tens_word} et un"]

        return [f"{tens_word} {UNITS[units_part]}"]

    if 70 <= number <= 79:
        if number == 71:
            return ["soixante et onze"]

        return [f"soixante {under_100_forms(number - 60)[0]}"]

    if number == 80:
        return ["quatre vingts"]

    if 81 <= number <= 99:
        return [
            f"quatre vingt {under_100_forms(number - 80)[0]}"
        ]

    raise ValueError("Неизвестная ошибка обработки числа")


def french_number_forms(number: int) -> list[str]:
    """
    Возвращает корректные французские формы числа от 0 до 999.
    """

    if not 0 <= number <= 999:
        raise ValueError("number должен быть в диапазоне 0..999")

    if number < 100:
        return under_100_forms(number)

    hundreds_part = number // 100
    rest = number % 100

    if hundreds_part == 1:
        prefix = "cent"
    else:
        # 200 = deux cents
        # 201 = deux cent un
        # 555 = cinq cent cinquante cinq
        cent_word = "cents" if rest == 0 else "cent"
        prefix = f"{UNITS[hundreds_part]} {cent_word}"

    if rest == 0:
        return [prefix]

    return [
        f"{prefix} {tail}"
        for tail in under_100_forms(rest)
    ]


# ============================================================
# СЛОВАРЬ ДОПУСТИМЫХ ФОРМ
# ============================================================

def build_number_dictionary() -> dict[str, int]:
    """
    Строит словарь:

    нормализованная французская запись -> арабское число.
    """

    result: dict[str, int] = {}

    for number in range(1000):
        for form in french_number_forms(number):
            result[normalise_key(form)] = number

    return result


NUMBER_BY_WORDS = build_number_dictionary()

KNOWN_WORDS = {
    word
    for phrase in NUMBER_BY_WORDS
    for word in phrase.split()
}


# ============================================================
# ПРЕОБРАЗОВАНИЕ ВВОДА
# ============================================================

def matches_number_range(words: list[str], start: int, end: int) -> bool:
    """Сверяет ветку с существующим словарём, не расширяя язык."""
    number = NUMBER_BY_WORDS.get(" ".join(words))
    return number is not None and start <= number <= end


def validate_units(words: list[str]) -> str | None:
    if matches_number_range(words, 0, 9):
        return None
    if "zero" in words:
        return (
            "Ошибка единичного формата: слово «zéro» "
            "может использоваться только отдельно."
        )
    return "Ошибка единичного формата: единицы записываются одним словом."


def validate_teens(words: list[str]) -> str | None:
    if matches_number_range(words, 10, 19):
        return None
    if words and words[0] == "dix":
        return (
            "Ошибка формата 10–19: после «dix» допустимо только "
            "одно из слов «sept», «huit», «neuf» либо конец числа."
        )
    return "Ошибка формата 10–19: числа 11–16 записываются одним словом без продолжения."


def validate_tens(words: list[str]) -> str | None:
    if matches_number_range(words, 20, 69):
        return None
    prefix = words[0]
    if len(words) > 1 and words[1] == "et":
        return (
            f"Ошибка десятичного формата: после «{prefix} et» "
            "допустимо только «un»."
        )
    if words[1:] == ["un"]:
        return (
            f"Ошибка десятичного формата: перед «un» нужна связка «et»: "
            f"«{prefix} et un»."
        )
    return (
        f"Ошибка десятичного формата: после «{prefix}» допустимы "
        "единицы 2–9, «et un» либо конец числа."
    )


def validate_70s(words: list[str]) -> str | None:
    if matches_number_range(words, 70, 79):
        return None
    tail = words[1:]
    if tail and tail[0] == "onze":
        return "Ошибка формата 70–79: число 71 требует связку «et»."
    if tail and tail[0] == "et":
        return (
            "Ошибка формата 70–79: после «soixante et» "
            "допустимо только «onze» для числа 71."
        )
    return (
        "Ошибка формата 70–79: после «soixante» требуется корректное число "
        "10–19; число 71 записывается «soixante et onze»."
    )


def validate_80_99(words: list[str]) -> str | None:
    if matches_number_range(words, 80, 99):
        return None
    if words[:2] not in (["quatre", "vingt"], ["quatre", "vingts"]):
        return "Ошибка формата 80–99: требуется основа «quatre vingt»."
    tail = words[2:]
    if words[1] == "vingts" and tail:
        return (
            "Ошибка формата 80–99: перед продолжением числа "
            "используется «vingt» без s."
        )
    if not tail:
        return "Ошибка формата 80–99: число 80 записывается «quatre vingts» с s."
    if "et" in tail:
        return "Ошибка формата 80–99: после «quatre vingt» связка «et» не используется."
    return "Ошибка формата 80–99: после «quatre vingt» требуется корректное число 1–19."


def validate_under_100(words: list[str]) -> str | None:
    """Выбирает ветку по основе и дополнению, как при построении дерева."""
    if matches_number_range(words, 0, 99):
        return None
    if not words:
        return "Ошибка синтаксического формата: ожидалось число 0–99."
    if "zero" in words:
        return validate_units(words)

    first = words[0]
    # «quatre» — единица, но «quatre vingt» — основа 80–99.
    if first == "vingts" or (
        first == "quatre" and any(word in {"vingt", "vingts"} for word in words[1:])
    ):
        return validate_80_99(words)

    teen_starts = {form.split()[0] for form in TEENS.values()}
    tail = words[1:]
    if tail and tail[0] == "et":
        tail = tail[1:]
    if first == "soixante" and tail and tail[0] in teen_starts:
        return validate_70s(words)
    if first in TENS.values():
        return validate_tens(words)
    if first in teen_starts:
        return validate_teens(words)
    if first in UNITS.values():
        return validate_units(words)
    return "Ошибка синтаксического формата: связка «et» не может начинать число."


def validate_hundreds(words: list[str]) -> str | None:
    if matches_number_range(words, 100, 999):
        return None
    positions = [i for i, word in enumerate(words) if word in {"cent", "cents"}]
    if len(positions) != 1:
        return "Ошибка сотенного формата: требуется ровно одно слово «cent» или «cents»."
    position = positions[0]
    prefix = words[:position]
    tail = words[position + 1:]
    if prefix and (len(prefix) != 1 or prefix[0] not in {UNITS[n] for n in range(2, 10)}):
        return (
            "Ошибка сотенного формата: перед «cent/cents» допустима "
            "одна единица 2–9; число 100 записывается «cent» без «un»."
        )
    cent_word = words[position]
    if cent_word == "cents" and tail:
        return (
            "Ошибка сотенного формата: перед продолжением числа "
            "используется «cent» без s."
        )
    if cent_word == "cents" and not prefix:
        return "Ошибка сотенного формата: число 100 записывается «cent» без s."
    if prefix and not tail and cent_word == "cent":
        return "Ошибка сотенного формата: для целых сотен 200–900 используется «cents» с s."
    if tail:
        error = validate_under_100(tail)
        if error:
            category, reason = error.split(": ", 1)
            return f"{category} в остатке после сотен: {reason}"
    return None


def convert_words_to_number(text: str) -> int:
    key = normalise_key(text)

    if not key:
        raise NumberInputError("Введите число словами.")

    if key in NUMBER_BY_WORDS:
        return NUMBER_BY_WORDS[key]

    words = key.split()
    for index, word in enumerate(words, start=1):
        if word not in KNOWN_WORDS:
            raise NumberInputError(
                f"Лексическая ошибка в слове №{index}: «{word}»."
            )

    if "zero" in words:
        error = validate_units(words)
    elif any(word in {"cent", "cents"} for word in words):
        error = validate_hundreds(words)
    else:
        error = validate_under_100(words)
    if error:
        raise NumberInputError(error)

    # Словарь остаётся единственным источником допустимых полных записей.
    raise NumberInputError(
        "Такое сочетание слов не является корректным "
        "французским числительным от 0 до 999."
    )


# ============================================================
# ПОСТРОЕНИЕ ДЕРЕВА РАЗБОРА
# ============================================================

def teen_tree(number: int, name: str = "Дополнение") -> TreeNode:
    """
    Строит дерево для чисел 10..19.

    10..16 имеют отдельные французские слова:
        onze, douze, treize...

    17..19 строятся как:
        dix + sept
        dix + huit
        dix + neuf
    """

    if not 10 <= number <= 19:
        raise ValueError("Ожидалось число 10..19")

    if number <= 16:
        return TreeNode(
            f"{name} ({number})",
            (
                terminal(TEENS[number]),
            )
        )

    units = number - 10

    return TreeNode(
        f"{name} ({number})",
        (
            TreeNode(
                "Десяток (10)",
                (
                    terminal("dix"),
                )
            ),
            TreeNode(
                f"Единицы ({units})",
                (
                    terminal(UNITS[units]),
                )
            ),
        )
    )


def under_100_tree_nodes(number: int) -> tuple[TreeNode, ...]:
    """
    Строит синтаксические узлы для французского числа 0..99.

    Здесь учитывается особенность французского языка:

    71 = 60 + 11
    75 = 60 + 15
    91 = 80 + 11
    """

    if not 0 <= number <= 99:
        raise ValueError("Ожидалось число 0..99")

    # --------------------------------------------------------
    # 0
    # --------------------------------------------------------

    if number == 0:
        return (
            TreeNode(
                "Ноль (0)",
                (
                    terminal("zéro"),
                )
            ),
        )

    # --------------------------------------------------------
    # 1..9
    # --------------------------------------------------------

    if number < 10:
        return (
            TreeNode(
                f"Единицы ({number})",
                (
                    terminal(UNITS[number]),
                )
            ),
        )

    # --------------------------------------------------------
    # 10..16
    # --------------------------------------------------------

    if 10 <= number <= 16:
        return (
            TreeNode(
                f"Число 10–16 ({number})",
                (
                    terminal(TEENS[number]),
                )
            ),
        )

    # --------------------------------------------------------
    # 17..19
    # dix-sept, dix-huit, dix-neuf
    # --------------------------------------------------------

    if 17 <= number <= 19:
        units = number - 10

        return (
            TreeNode(
                "Десяток (10)",
                (
                    terminal("dix"),
                )
            ),
            TreeNode(
                f"Единицы ({units})",
                (
                    terminal(UNITS[units]),
                )
            ),
        )

    # --------------------------------------------------------
    # 20..69
    # --------------------------------------------------------

    if 20 <= number <= 69:
        tens = number // 10 * 10
        units = number % 10

        nodes: list[TreeNode] = [
            TreeNode(
                f"Десятки ({tens})",
                (
                    terminal(TENS[tens]),
                )
            )
        ]

        if units == 1:
            nodes.append(
                TreeNode(
                    "Связка",
                    (
                        terminal("et"),
                    )
                )
            )

        if units != 0:
            nodes.append(
                TreeNode(
                    f"Единицы ({units})",
                    (
                        terminal(UNITS[units]),
                    )
                )
            )

        return tuple(nodes)

    # --------------------------------------------------------
    # 70..79
    #
    # 70 = 60 + 10
    # 71 = 60 + 11
    # 72 = 60 + 12
    # ...
    # --------------------------------------------------------

    if 70 <= number <= 79:
        rest = number - 60

        nodes = [
            TreeNode(
                "Десятки (60)",
                (
                    terminal("soixante"),
                )
            )
        ]

        if number == 71:
            nodes.append(
                TreeNode(
                    "Связка",
                    (
                        terminal("et"),
                    )
                )
            )

        nodes.append(
            teen_tree(rest)
        )

        return tuple(nodes)

    # --------------------------------------------------------
    # 80
    #
    # quatre vingts
    # --------------------------------------------------------

    if number == 80:
        return (
            TreeNode(
                "Десятки (80)",
                (
                    terminal("quatre"),
                    terminal("vingts"),
                )
            ),
        )

    # --------------------------------------------------------
    # 81..99
    #
    # 81 = 80 + 1
    # 91 = 80 + 11
    # --------------------------------------------------------

    if 81 <= number <= 99:
        rest = number - 80

        nodes = [
            TreeNode(
                "Десятки (80)",
                (
                    terminal("quatre"),
                    terminal("vingt"),
                )
            )
        ]

        if rest < 10:
            nodes.append(
                TreeNode(
                    f"Единицы ({rest})",
                    (
                        terminal(UNITS[rest]),
                    )
                )
            )
        else:
            nodes.append(
                teen_tree(rest)
            )

        return tuple(nodes)

    raise ValueError("Ошибка построения дерева")


def build_parse_tree(number: int) -> TreeNode:
    """
    Формирует полное дерево разбора числа 0..999.
    """

    if not 0 <= number <= 999:
        raise ValueError("Ожидалось число 0..999")

    children: list[TreeNode] = []

    # --------------------------------------------------------
    # Сотни
    # --------------------------------------------------------

    if number >= 100:
        hundreds_digit = number // 100
        hundreds_value = hundreds_digit * 100
        rest = number % 100

        hundred_children: list[TreeNode] = []

        if hundreds_digit == 1:
            # 100 = cent, а не un cent
            hundred_children.append(
                terminal("cent")
            )
        else:
            hundred_children.append(
                terminal(UNITS[hundreds_digit])
            )

            cent_word = "cents" if rest == 0 else "cent"

            hundred_children.append(
                terminal(cent_word)
            )

        children.append(
            TreeNode(
                f"Сотни ({hundreds_value})",
                tuple(hundred_children)
            )
        )

        if rest != 0:
            children.extend(
                under_100_tree_nodes(rest)
            )

    else:
        children.extend(
            under_100_tree_nodes(number)
        )

    return TreeNode(
        f"Французское число\n{number}",
        tuple(children)
    )


# ============================================================
# ГРАФИЧЕСКИЙ ИНТЕРФЕЙС
# ============================================================

class NumberConverterApp(tk.Tk):

    def __init__(self) -> None:
        super().__init__()

        self.title("Перевод числа с французского")
        self.geometry("960x680")
        self.minsize(850, 600)

        self.configure(
            padx=18,
            pady=16
        )

        self.words_var = tk.StringVar()
        self.number_var = tk.StringVar(value="0")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        main = ttk.Frame(
            self,
            padding=4
        )
        main.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        main.columnconfigure(0, weight=1)
        main.rowconfigure(6, weight=1)

        # ----------------------------------------------------
        # Ввод
        # ----------------------------------------------------

        ttk.Label(
            main,
            text="Число словами (французский)"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 4)
        )

        self.input_box = ttk.Entry(
            main,
            textvariable=self.words_var,
            width=54
        )
        self.input_box.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(0, 16)
        )

        # ----------------------------------------------------
        # Результат
        # ----------------------------------------------------

        ttk.Label(
            main,
            text="Число арабскими цифрами"
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(0, 4)
        )

        ttk.Entry(
            main,
            textvariable=self.number_var,
            width=28,
            state="readonly"
        ).grid(
            row=3,
            column=0,
            sticky="w",
            pady=(0, 16)
        )

        # ----------------------------------------------------
        # Кнопка
        # ----------------------------------------------------

        ttk.Button(
            main,
            text="Перевести",
            command=self.translate
        ).grid(
            row=4,
            column=0,
            sticky="w",
            pady=(0, 16)
        )

        # ----------------------------------------------------
        # Поле дерева разбора
        # ----------------------------------------------------

        tree_frame = ttk.LabelFrame(
            main,
            text="Дерево синтаксического разбора",
            padding=8
        )
        tree_frame.grid(
            row=6,
            column=0,
            sticky="nsew"
        )

        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree_canvas = tk.Canvas(
            tree_frame,
            background="white",
            height=360,
            highlightthickness=1,
            highlightbackground="#bcbcbc"
        )

        self.tree_canvas.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        horizontal_scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="horizontal",
            command=self.tree_canvas.xview
        )

        horizontal_scrollbar.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        vertical_scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.tree_canvas.yview
        )

        vertical_scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.tree_canvas.configure(
            xscrollcommand=horizontal_scrollbar.set,
            yscrollcommand=vertical_scrollbar.set
        )

        # ----------------------------------------------------
        # Enter = перевод
        # ----------------------------------------------------

        self.input_box.bind(
            "<Return>",
            lambda _event: self.translate()
        )

        self.input_box.focus_set()

        self.show_tree_message(
            "После перевода здесь появится дерево разбора"
        )

    # ========================================================
    # ВЫВОД СООБЩЕНИЯ В CANVAS
    # ========================================================

    def show_tree_message(self, message: str) -> None:
        self.tree_canvas.delete("all")

        self.tree_canvas.create_text(
            420,
            170,
            text=message,
            font=("TkDefaultFont", 11),
            fill="#666666"
        )

        self.tree_canvas.configure(
            scrollregion=(0, 0, 840, 340)
        )

    # ========================================================
    # ОТРИСОВКА ДЕРЕВА
    # ========================================================

    def draw_parse_tree(self, root: TreeNode) -> None:
        """
        Рисует дерево сверху вниз.

        Каждый нетерминал/терминал представлен прямоугольником,
        дочерние конструкции соединяются линиями.
        """

        self.tree_canvas.delete("all")

        horizontal_step = 185
        vertical_step = 105

        margin_x = 60
        margin_y = 45

        box_width = 150
        box_height = 52

        # ----------------------------------------------------
        # Считаем ширину поддеревьев.
        #
        # Один лист = одно место по горизонтали.
        # ----------------------------------------------------

        subtree_widths: dict[int, int] = {}

        def calculate_width(node: TreeNode) -> int:
            if not node.children:
                width = 1
            else:
                width = sum(
                    calculate_width(child)
                    for child in node.children
                )

            subtree_widths[id(node)] = width

            return width

        total_slots = calculate_width(root)

        # ----------------------------------------------------
        # Считаем максимальную глубину.
        # ----------------------------------------------------

        def calculate_depth(node: TreeNode) -> int:
            if not node.children:
                return 1

            return 1 + max(
                calculate_depth(child)
                for child in node.children
            )

        max_depth = calculate_depth(root)

        # ----------------------------------------------------
        # Определяем координаты всех узлов.
        # ----------------------------------------------------

        positions: dict[int, tuple[float, float]] = {}

        def place_node(
            node: TreeNode,
            depth: int,
            start_slot: float
        ) -> None:

            subtree_width = subtree_widths[id(node)]

            center_slot = (
                start_slot
                + subtree_width / 2
            )

            x = (
                margin_x
                + center_slot * horizontal_step
            )

            y = (
                margin_y
                + depth * vertical_step
            )

            positions[id(node)] = (x, y)

            current_slot = start_slot

            for child in node.children:
                place_node(
                    child,
                    depth + 1,
                    current_slot
                )

                current_slot += subtree_widths[id(child)]

        place_node(
            root,
            depth=0,
            start_slot=0
        )

        # ----------------------------------------------------
        # Сначала рисуем линии.
        # ----------------------------------------------------

        def draw_edges(node: TreeNode) -> None:
            parent_x, parent_y = positions[id(node)]

            for child in node.children:
                child_x, child_y = positions[id(child)]

                self.tree_canvas.create_line(
                    parent_x,
                    parent_y + box_height / 2,
                    child_x,
                    child_y - box_height / 2,
                    fill="black",
                    width=2
                )

                draw_edges(child)

        draw_edges(root)

        # ----------------------------------------------------
        # Затем прямоугольники поверх линий.
        # ----------------------------------------------------

        def draw_nodes(node: TreeNode) -> None:
            x, y = positions[id(node)]

            self.tree_canvas.create_rectangle(
                x - box_width / 2,
                y - box_height / 2,
                x + box_width / 2,
                y + box_height / 2,
                fill="white",
                outline="black",
                width=2
            )

            self.tree_canvas.create_text(
                x,
                y,
                text=node.label,
                width=box_width - 12,
                justify="center",
                fill="black",
                font=("Arial", 11)
            )

            for child in node.children:
                draw_nodes(child)

        draw_nodes(root)

        # ----------------------------------------------------
        # Размер виртуального полотна.
        # ----------------------------------------------------

        canvas_width = max(
            850,
            total_slots * horizontal_step + margin_x * 2
        )

        canvas_height = max(
            340,
            max_depth * vertical_step + margin_y * 2
        )

        self.tree_canvas.configure(
            scrollregion=(
                0,
                0,
                canvas_width,
                canvas_height
            )
        )

        self.tree_canvas.xview_moveto(0)
        self.tree_canvas.yview_moveto(0)

    # ========================================================
    # ПЕРЕВОД
    # ========================================================

    def translate(self) -> None:
        try:
            number = convert_words_to_number(
                self.words_var.get()
            )

            self.number_var.set(
                str(number)
            )

            tree = build_parse_tree(number)

            self.draw_parse_tree(tree)

        except NumberInputError as error:
            self.number_var.set("0")

            self.show_tree_message(
                "Дерево не построено:\n"
                "во входной последовательности найдена ошибка"
            )

            messagebox.showerror(
                "Ошибка",
                str(error),
                parent=self
            )


if __name__ == "__main__":
    NumberConverterApp().mainloop()