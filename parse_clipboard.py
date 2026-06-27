import os
import re
import glob
import sys

try:
    import pyperclip
except ImportError:
    print("❌ Ошибка: Библиотека 'pyperclip' не установлена!")
    print("Установите её командой: pip install pyperclip")
    sys.exit(1)


def update_main_typ():
    """Автоматическое обновление файла main.typ на основе всех существующих ticket.typ"""
    base_dir = "Билеты"
    tickets = sorted(glob.glob(os.path.join(base_dir, "Билет *", "ticket.typ")))

    if not tickets:
        print("⚠️ Папки с билетами или файлы ticket.typ не найдены для обновления main.typ")
        return

    imports = []
    with open("main.typ", "w", encoding="utf-8") as f:
        f.write('#import "make-cards.typ": make-cards\n\n')

        for ticket_path in tickets:
            folder_name = os.path.basename(os.path.dirname(ticket_path))
            match = re.search(r'Билет (\d+)', folder_name)
            if match:
                num = match.group(1)
                f.write(f'#import "Билеты/{folder_name}/ticket.typ": ticket as t{num}\n')
                imports.append(f"t{num}")

        f.write('\n// Сборка всех готовых карточек\n')
        f.write('#make-cards((\n')
        for imp in imports:
            f.write(f'  {imp},\n')
        f.write('))\n')
    print("🔄 Файл main.typ успешно обновлен!")


def main():
    print("📋 Чтение буфера обмена...")
    text = pyperclip.paste()

    if not text.strip():
        print("❌ Буфер обмена пуст!")
        return

    # Регулярное выражение для поиска блоков кода Typst с указанием пути к файлу
    pattern = r"### ФАЙЛ:\s*Билет\s*(\d+).*?```(?:typst)?\s*(.*?)\s*```"
    matches = list(re.finditer(pattern, text, re.DOTALL | re.IGNORECASE))

    if not matches:
        print("❌ В буфере обмена не найдено подходящих блоков кода Typst!")
        print("Убедитесь, что скопировали ответ нейросети целиком, включая заголовки '### ФАЙЛ: Билет XX/ticket.typ'.")
        return

    print(f"🔍 Найдено билетов в буфере: {len(matches)}")
    for match in matches:
        num = int(match.group(1))
        print(f"  - Билет {num:02d}")

    # Запрос подтверждения
    confirm = input("\nЗаписать эти билеты в соответствующие папки? [Y/n]: ").strip().lower()
    if confirm not in ['', 'y', 'yes', 'д', 'да']:
        print("❌ Операция отменена.")
        return

    base_dir = "Билеты"
    updated_count = 0

    for match in matches:
        ticket_num = int(match.group(1))
        typst_code = match.group(2).strip()

        # Ищем папку этого билета (например, "Билеты/Билет 05 ...")
        search_pattern = os.path.join(base_dir, f"Билет {ticket_num:02d}*")
        matching_folders = glob.glob(search_pattern)

        if not matching_folders:
            print(f"⚠️ Папка для Билета {ticket_num:02d} не найдена! Пропуск. (Искали: {search_pattern})")
            continue

        folder_path = matching_folders[0]
        out_file_path = os.path.join(folder_path, "ticket.typ")

        try:
            with open(out_file_path, "w", encoding="utf-8") as f:
                f.write(typst_code)
            print(f"💾 Успешно записан: {out_file_path}")
            updated_count += 1
        except Exception as e:
            print(f"❌ Ошибка записи Билета {ticket_num:02d}: {e}")

    print(f"\n✅ Результат: Обновлено билетов: {updated_count} из {len(matches)}")

    if updated_count > 0:
        update_main_typ()


if __name__ == "__main__":
    main()