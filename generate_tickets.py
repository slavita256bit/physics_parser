import os
import glob
import re
import subprocess
import tempfile
import time  # <--- Добавлен импорт для задержки
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Загрузка переменных окружения из файла .env
load_dotenv()

# Инициализация клиента
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


def verify_typst_compilation(file_path):
    """
    Пытается скомпилировать typst-файл во временный PDF для проверки на ошибки.
    Требует установленного typst CLI в системе.
    """
    try:
        # Создаем временный файл для вывода компиляции
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            temp_pdf = tmp.name

        # Запуск компиляции
        result = subprocess.run(
            ["typst", "compile", file_path, temp_pdf],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )

        # Удаляем временный PDF
        if os.path.exists(temp_pdf):
            try:
                os.remove(temp_pdf)
            except:
                pass

        if result.returncode == 0:
            return True, ""
        else:
            return False, result.stderr

    except FileNotFoundError:
        # Если утилита typst не установлена в PATH
        return True, "WARNING_NO_TYPST"
    except Exception as e:
        return False, str(e)


def update_main_typ():
    """Собирает main.typ на основе всех существующих ticket.typ"""
    base_dir = "Билеты"
    tickets = sorted(glob.glob(os.path.join(base_dir, "Билет *", "ticket.typ")))

    if not tickets:
        return

    print("\n🔄 Обновление файла main.typ...")
    with open("main.typ", "w", encoding="utf-8") as f:
        f.write('#import "make-cards.typ": make-cards\n\n')

        imports = []
        for ticket_path in tickets:
            folder_name = os.path.basename(os.path.dirname(ticket_path))
            match = re.search(r'Билет (\d+)', folder_name)
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
    for file in os.listdir(ticket_dir):
        if file == "ticket.typ":
            continue

        ext = file.lower().split('.')[-1]
        if ext in ['pdf', 'png', 'jpg', 'jpeg']:
            files_to_upload.append(os.path.join(ticket_dir, file))

    if not files_to_upload:
        print("⚠️ Нет файлов для анализа. Пропуск.")
        return False

    uploaded_files = []
    try:
        # 1. Загружаем файлы в File API
        print(f"⬆️ Загрузка файлов в Gemini ({len(files_to_upload)} шт.)...")
        for file_path in files_to_upload:
            uploaded_file = client.files.upload(file=file_path)
            uploaded_files.append(uploaded_file)

        # 2. Настройки генерации (включая thinking budget)
        # Бюджет в 2048 байт соответствует среднему значению рассуждений (medium)
        config = types.GenerateContentConfig(
            system_instruction=sys_prompt,
            temperature=0.2,
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(thinking_budget=2048)
        )

        # Рекомендуется использовать gemini-3.5-flash для корректной поддержки thinking_config
        model_name = 'models/gemini-3.5-flash'

        # Создаем сессию чата для возможности ведения диалога и исправления ошибок
        chat = client.chats.create(
            model=model_name,
            config=config
        )

        print("⏳ Ожидание ответа от нейросети (первая попытка)...")
        contents = uploaded_files + [f"Название билета: {folder_name}"]
        response = chat.send_message(contents)

        # 3. Сохраняем результат
        typst_code = extract_typst_code(response.text)
        out_path = os.path.join(ticket_dir, "ticket.typ")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(typst_code)

        # 4. Проверка компиляции
        print("🔍 Проверка компиляции Typst...")
        is_ok, err_msg = verify_typst_compilation(out_path)

        if is_ok:
            if err_msg == "WARNING_NO_TYPST":
                print("⚠️ Предупреждение: утилита 'typst' не найдена в системе. Проверка компиляции пропущена.")
            else:
                print(f"✅ Успешно сгенерирован и скомпилирован: {out_path}")
            return True
        else:
            # Если компиляция не удалась, отправляем ошибку в этот же чат для исправления (один раз)
            print(f"❌ Ошибка компиляции Typst. Запрос исправления у модели...\nДетали ошибки:\n{err_msg}")

            # Небольшая пауза перед повторным запросом исправления, чтобы снизить нагрузку
            time.sleep(10)

            correction_prompt = (
                f"При компиляции сгенерированного кода Typst произошла ошибка:\n\n"
                f"{err_msg}\n\n"
                f"Пожалуйста, проанализируй и исправь эту ошибку. "
                f"Выдай исправленный код в соответствии со всеми правилами (только один блок ```typst ... ``` без комментариев)."
            )

            print("⏳ Ожидание исправленной версии...")
            retry_response = chat.send_message(correction_prompt)

            typst_code_fixed = extract_typst_code(retry_response.text)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(typst_code_fixed)

            # Повторная финальная проверка для логов
            is_ok_final, final_msg = verify_typst_compilation(out_path)
            if is_ok_final:
                print(f"✅ Успешно исправлено и сгенерировано: {out_path}")
                return True
            else:
                print(f"❌ Повторная компиляция также завершилась ошибкой. Файл сохранен «как есть» для ручной правки.")
                return False

    except Exception as e:
        print(f"❌ Ошибка при обработке {folder_name}: {e}")
        return False

    finally:
        # 5. ОЧИСТКА файлов из облака
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

    all_ticket_dirs = sorted(glob.glob(os.path.join(base_dir, "Билет *")))

    if not all_ticket_dirs:
        print("Не найдено ни одной папки с билетами.")
        return

    print(f"Найдено билетов: {len(all_ticket_dirs)}")

    start_str = input("Введите начальный номер билета (оставьте пустым для начала с первого): ").strip()
    end_str = input("Введите конечный номер билета (оставьте пустым для обработки до конца): ").strip()

    start_num = int(start_str) if start_str else 0
    end_num = int(end_str) if end_str else 999

    dirs_to_process = []
    for t_dir in all_ticket_dirs:
        match = re.search(r'Билет (\d+)', os.path.basename(t_dir))
        if match:
            num = int(match.group(1))
            if start_num <= num <= end_num:
                dirs_to_process.append(t_dir)

    print(f"\nК обработке выбрано билетов: {len(dirs_to_process)}")

    # Задержка между билетами (в секундах) для обхода лимитов бесплатного тарифа (например, 12 секунд)
    delay_between_tickets = 60

    for i, t_dir in enumerate(dirs_to_process):
        # Если это не первый обрабатываемый билет, делаем паузу перед запросом
        if i > 0:
            print(f"💤 Ожидание {delay_between_tickets} сек. для предотвращения лимитов API...")
            time.sleep(delay_between_tickets)

        process_ticket(t_dir, sys_prompt)

    update_main_typ()


if __name__ == "__main__":
    main()