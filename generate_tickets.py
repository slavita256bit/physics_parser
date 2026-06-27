import os
import glob
import re
from google import genai
from google.genai import types

# Инициализация клиента
# Скрипт автоматически подхватит ключ из переменной окружения GEMINI_API_KEY
client = genai.Client()


def get_system_prompt():
    prompt_path = "ticket_prompt.md"
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Файл {prompt_path} не найден! Создайте его и поместите туда системный промпт.")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_typst_code(text):
    """Вырезает код из Markdown-блоков ответа нейросети"""
    if "```typst" in text:
        return text.split("```typst")[1].split("```")[0].strip()
    elif "```" in text:
        return text.split("```")[1].split("```")[0].strip()
    return text.strip()


def update_main_typ():
    """Собирает main.typ на основе всех существующих ticket.typ"""
    base_dir = "Билеты"
    tickets = sorted(glob.glob(os.path.join(base_dir, "Билет_*", "ticket.typ")))

    if not tickets:
        return

    print("\n🔄 Обновление файла main.typ...")
    with open("main.typ", "w", encoding="utf-8") as f:
        f.write('#import "flashcards.typ": make-cards\n\n')

        imports = []
        for ticket_path in tickets:
            # Извлекаем имя папки (например, "Билет_04_Закон_Кулона")
            folder_name = os.path.basename(os.path.dirname(ticket_path))
            match = re.search(r'Билет_(\d+)', folder_name)
            if match:
                num = match.group(1)
                f.write(f'#import "Билеты/{folder_name}/ticket.typ": ticket as t{num}\n')
                imports.append(f't{num}')

        f.write('\n// Сборка всех готовых карточек\n')
        f.write('#make-cards((\n')
        for imp in imports:
            f.write(f'  {imp},\n')
        f.write('))\n')
    print("✅ main.typ успешно обновлен!")


def process_ticket(ticket_dir, sys_prompt):
    folder_name = os.path.basename(ticket_dir)
    print(f"\n{"=" * 40}\nОбработка: {folder_name}")

    files_to_upload = []
    # Собираем все PDF и картинки из папки
    for file in os.listdir(ticket_dir):
        if file == "ticket.typ":
            continue  # Игнорируем уже сгенерированный файл

        ext = file.lower().split('.')[-1]
        if ext in ['pdf', 'png', 'jpg', 'jpeg']:
            files_to_upload.append(os.path.join(ticket_dir, file))

    if not files_to_upload:
        print("⚠️ Нет файлов для анализа. Пропуск.")
        return False

    uploaded_files = []
    try:
        # 1. Загружаем файлы в File API Google (Обязательно для PDF)
        print(f"⬆️ Загрузка файлов в Gemini ({len(files_to_upload)} шт.)...")
        for file_path in files_to_upload:
            uploaded_file = client.files.upload(file=file_path)
            uploaded_files.append(uploaded_file)

        # 2. Формируем запрос
        print("⏳ Ожидание ответа от нейросети...")

        # Передаем загруженные файлы и название папки как текстовый промпт
        contents = uploaded_files + [f"Название билета: {folder_name}"]

        # Настройки генерации
        # Температуру поставил 0.2 (вместо 1), чтобы код Typst был более строгим и без галлюцинаций
        config = types.GenerateContentConfig(
            system_instruction=sys_prompt,
            temperature=0.2,
            max_output_tokens=8192,
        )

        response = client.models.generate_content(
            model='models/gemini-3.5-flash',
            contents=contents,
            config=config
        )

        # 3. Сохраняем результат
        typst_code = extract_typst_code(response.text)
        out_path = os.path.join(ticket_dir, "ticket.typ")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(typst_code)

        print(f"✅ Успешно сгенерирован: {out_path}")
        return True

    except Exception as e:
        print(f"❌ Ошибка при обработке {folder_name}: {e}")
        return False

    finally:
        # 4. ОЧИСТКА. Обязательно удаляем файлы из облака Gemini,
        # иначе быстро закончится квота в 20 ГБ на хранение файлов.
        for uf in uploaded_files:
            try:
                client.files.delete(name=uf.name)
            except:
                pass


def main():
    try:
        sys_prompt = get_system_prompt()
    except Exception as e:
        print(e)
        return

    base_dir = "Билеты"
    if not os.path.exists(base_dir):
        print(f"Папка '{base_dir}' не найдена!")
        return

    # Получаем все папки билетов и сортируем их
    all_ticket_dirs = sorted(glob.glob(os.path.join(base_dir, "Билет_*")))

    if not all_ticket_dirs:
        print("Не найдено ни одной папки с билетами.")
        return

    print(f"Найдено билетов: {len(all_ticket_dirs)}")

    # Ввод диапазона
    start_str = input("Введите начальный номер билета (оставьте пустым для начала с первого): ").strip()
    end_str = input("Введите конечный номер билета (оставьте пустым для обработки до конца): ").strip()

    start_num = int(start_str) if start_str else 0
    end_num = int(end_str) if end_str else 999

    # Фильтруем папки по диапазону
    dirs_to_process = []
    for t_dir in all_ticket_dirs:
        match = re.search(r'Билет_(\d+)', os.path.basename(t_dir))
        if match:
            num = int(match.group(1))
            if start_num <= num <= end_num:
                dirs_to_process.append(t_dir)

    print(f"\nК обработке выбрано билетов: {len(dirs_to_process)}")

    for t_dir in dirs_to_process:
        process_ticket(t_dir, sys_prompt)

    # В конце всегда обновляем main.typ
    update_main_typ()


if __name__ == "__main__":
    main()