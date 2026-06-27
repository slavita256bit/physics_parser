import os
import glob
import re


def update_main_typ():
    base_dir = "Билеты"

    # Находим все файлы ticket.typ во вложенных папках
    tickets = sorted(glob.glob(os.path.join(base_dir, "Билет *", "ticket.typ")))

    if not tickets:
        print("❌ Ошибка: В папке 'Билеты' не найдено ни одного файла 'ticket.typ'!")
        return

    print(f"🔍 Найдено готовых билетов для сборки: {len(tickets)}")

    imports = []

    # Открываем и перезаписываем файл main.typ
    with open("main.typ", "w", encoding="utf-8") as f:
        f.write('#import "make-cards.typ": make-cards\n\n')

        for ticket_path in tickets:
            # Извлекаем имя папки (например, "Билет 01 Электрический заряд...")
            folder_name = os.path.basename(os.path.dirname(ticket_path))

            # Извлекаем двухзначный номер билета регулярным выражением
            match = re.search(r'Билет (\d+)', folder_name)
            if match:
                num = match.group(1)  # Например, "01", "10"
                f.write(f'#import "Билеты/{folder_name}/ticket.typ": ticket as t{num}\n')
                imports.append(f"t{num}")

        f.write('\n// Сборка всех готовых карточек\n')
        f.write('#make-cards((\n')
        for imp in imports:
            f.write(f'  {imp},\n')
        f.write('))\n')

    print("✅ Файл 'main.typ' успешно обновлен и структурирован!")


if __name__ == "__main__":
    update_main_typ()