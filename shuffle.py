import tkinter as tk
from tkinter import messagebox


def mix_sentences():
    # Получаем текст и убираем лишние пробелы
    text1 = input_field1.get().strip()
    text2 = input_field2.get().strip()

    # Проверка пустых полей
    if not text1 or not text2:
        messagebox.showerror(
            "Ошибка",
            "Оба поля должны быть заполнены."
        )
        return

    # Разбиваем предложения на слова
    words1 = text1.split()
    words2 = text2.split()

    # Проверяем количество слов
    if len(words1) != len(words2):
        messagebox.showerror(
            "Ошибка",
            f"Количество слов должно совпадать!\n\n"
            f"В первом предложении: {len(words1)} слов\n"
            f"Во втором предложении: {len(words2)} слов"
        )
        return

    # Перемешиваем слова в шахматном порядке
    result_words = []

    for i in range(len(words1)):
        result_words.append(words1[i])
        result_words.append(words2[i])

    result = " ".join(result_words)

    # Выводим результат
    output_field.config(state="normal")
    output_field.delete(0, tk.END)
    output_field.insert(0, result)
    output_field.config(state="readonly")


# Создание окна
window = tk.Tk()
window.title("Перемешивание предложений")
window.geometry("550x280")
window.resizable(False, False)


# Первое предложение
label1 = tk.Label(window, text="Первое предложение:")
label1.pack(pady=(20, 5))

input_field1 = tk.Entry(window, width=65)
input_field1.pack()


# Второе предложение
label2 = tk.Label(window, text="Второе предложение:")
label2.pack(pady=(15, 5))

input_field2 = tk.Entry(window, width=65)
input_field2.pack()


# Кнопка
mix_button = tk.Button(
    window,
    text="Перемешать",
    command=mix_sentences,
    width=20
)
mix_button.pack(pady=20)


# Результат
output_label = tk.Label(window, text="Результат:")
output_label.pack(pady=(0, 5))

output_field = tk.Entry(window, width=65, state="readonly")
output_field.pack()


window.mainloop()