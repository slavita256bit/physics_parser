import os
import json
import glob
import re
from pypdf import PdfReader, PdfWriter


def merge_json_configs(config_dir):
    merged_config = {}
    json_files = glob.glob(os.path.join(config_dir, "*.json"))
    for file_path in json_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged_config.update(data)
        except Exception as e:
            print(f"Ошибка чтения файла {file_path}: {e}")
    return merged_config


def main():
    notes_pdf_path = "notes.pdf"
    seo_folder = "seo_docs"
    saveliev_2_path = "Савельев_Том_2.pdf"
    saveliev_3_path = "Савельев_Том_3.pdf"
    config_dir = "configs"
    batches_output_dir = "batches"

    print("--- Старт умной подготовки батчей для Gemini ---")

    config = merge_json_configs(config_dir)
    if not config:
        print(f"Ошибка! В папке '{config_dir}' не найдено конфигураций .json.")
        return

    notes_reader = PdfReader(notes_pdf_path) if os.path.exists(notes_pdf_path) else None
    sav2_reader = PdfReader(saveliev_2_path) if os.path.exists(saveliev_2_path) else None
    sav3_reader = PdfReader(saveliev_3_path) if os.path.exists(saveliev_3_path) else None
    seo_readers = {}

    start_str = input("Введите начальный номер билета (по умолчанию 1): ").strip()
    end_str = input("Введите конечный номер билета (по умолчанию до упора): ").strip()
    batch_size_str = input("Размер батча (по умолчанию 10): ").strip()

    start_num = int(start_str) if start_str else 1
    end_num = int(end_str) if end_str else 999
    batch_size = int(batch_size_str) if batch_size_str else 10

    active_tickets = []
    for t_num_str, t_data in config.items():
        t_num = int(t_num_str)
        if start_num <= t_num <= end_num:
            active_tickets.append((t_num, t_data))

    active_tickets.sort(key=lambda x: x[0])

    if not active_tickets:
        print("В указанном диапазоне билеты не найдены в конфигурации.")
        return

    print(f"Всего билетов к обработке: {len(active_tickets)}")

    for i in range(0, len(active_tickets), batch_size):
        chunk = active_tickets[i: i + batch_size]
        batch_start_num = chunk[0][0]
        batch_end_num = chunk[-1][0]

        batch_folder_name = f"batch_{batch_start_num:02d}_{batch_end_num:02d}"
        batch_path = os.path.join(batches_output_dir, batch_folder_name)
        os.makedirs(batch_path, exist_ok=True)

        print(f"\n📂 Сборка батча {batch_folder_name} (билеты с {batch_start_num} по {batch_end_num})...")

        # --- ШАГ 1: Поиск уникальных страниц для батча ---
        notes_pages_set = set()
        seo_pages_set = set()  # Хранит кортежи (seo_filename, page_num)
        saveliev_pages_set = set()  # Хранит кортежи (volume, page_num)

        for _, t_data in chunk:
            # Рукописные заметки
            for p in t_data.get("notes_pdf", []):
                notes_pages_set.add(p)

            # СЭО
            seo_filename = t_data.get("seo_pdf")
            for p in t_data.get("seo_pages", []):
                if seo_filename:
                    seo_pages_set.add((seo_filename, p))

            # Савельев
            sav_vol = t_data.get("sav_vol")
            for p in t_data.get("sav_pages", []):
                if sav_vol:
                    saveliev_pages_set.add((sav_vol, p))

        unique_notes_pages = sorted(list(notes_pages_set))
        unique_seo_pages = sorted(list(seo_pages_set), key=lambda x: (x[0], x[1]))
        unique_sav_pages = sorted(list(saveliev_pages_set), key=lambda x: (x[0], x[1]))

        # --- ШАГ 2: Генерация объединенных PDF-файлов ---

        # 2.1 Конспект
        if unique_notes_pages and notes_reader:
            writer = PdfWriter()
            for p in unique_notes_pages:
                if p - 1 < len(notes_reader.pages):
                    writer.add_page(notes_reader.pages[p - 1])
            with open(os.path.join(batch_path, "notes_combined.pdf"), "wb") as f:
                writer.write(f)

        # 2.2 СЭО
        if unique_seo_pages:
            writer = PdfWriter()
            for seo_filename, p in unique_seo_pages:
                seo_filepath = os.path.join(seo_folder, seo_filename)
                if os.path.exists(seo_filepath):
                    if seo_filename not in seo_readers:
                        seo_readers[seo_filename] = PdfReader(seo_filepath)
                    reader = seo_readers[seo_filename]
                    if p - 1 < len(reader.pages):
                        writer.add_page(reader.pages[p - 1])
            with open(os.path.join(batch_path, "seo_combined.pdf"), "wb") as f:
                writer.write(f)

        # 2.3 Савельев
        if unique_sav_pages:
            writer = PdfWriter()
            for sav_vol, p in unique_sav_pages:
                reader = sav2_reader if sav_vol == 2 else sav3_reader
                if reader:
                    offset = 10 if sav_vol == 2 else 0
                    if p + offset < len(reader.pages):
                        writer.add_page(reader.pages[p + offset])
            with open(os.path.join(batch_path, "saveliev_combined.pdf"), "wb") as f:
                writer.write(f)

        # --- ШАГ 3: Создание маппингов для манифеста (1-based индексы в новых файлах) ---
        notes_map = {p: idx + 1 for idx, p in enumerate(unique_notes_pages)}
        seo_map = {entry: idx + 1 for idx, entry in enumerate(unique_seo_pages)}
        sav_map = {entry: idx + 1 for idx, entry in enumerate(unique_sav_pages)}

        # --- ШАГ 4: Запись подробного манифеста ---
        manifest_lines = [
            f"=== БАТЧ: Билеты {batch_start_num:02d}-{batch_end_num:02d} ===",
            "Все необходимые страницы объединены в общие файлы во избежание дублирования.",
            "Работай строго по указанным страницам из манифеста ниже.\n"
        ]

        for t_num, t_data in chunk:
            title = t_data.get("title", f"Билет_{t_num}")
            manifest_lines.append(f"Билет {t_num:02d}: {title}")

            # Картографирование конспекта
            t_notes = t_data.get("notes_pdf", [])
            if t_notes and notes_reader:
                mapped_pages = [str(notes_map[p]) for p in t_notes if p in notes_map]
                manifest_lines.append(f"  - Конспект (notes_combined.pdf): страницы {', '.join(mapped_pages)}")
            else:
                manifest_lines.append("  - Конспект: не требуется")

            # Картографирование СЭО
            t_seo_file = t_data.get("seo_pdf")
            t_seo_pages = t_data.get("seo_pages", [])
            if t_seo_file and t_seo_pages:
                mapped_pages = [str(seo_map[(t_seo_file, p)]) for p in t_seo_pages if (t_seo_file, p) in seo_map]
                manifest_lines.append(f"  - СЭО (seo_combined.pdf): страницы {', '.join(mapped_pages)}")
            else:
                manifest_lines.append("  - СЭО: не требуется")

            # Картографирование Савельева
            t_sav_vol = t_data.get("sav_vol")
            t_sav_pages = t_data.get("sav_pages", [])
            if t_sav_vol and t_sav_pages:
                mapped_pages = [str(sav_map[(t_sav_vol, p)]) for p in t_sav_pages if (t_sav_vol, p) in sav_map]
                manifest_lines.append(f"  - Савельев (saveliev_combined.pdf): страницы {', '.join(mapped_pages)}")
            else:
                manifest_lines.append("  - Савельев: не требуется")

            manifest_lines.append("")  # Пустая строка для читаемости

        with open(os.path.join(batch_path, "manifest.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(manifest_lines))

        print(f"✅ Батч {batch_folder_name} успешно собран!")

    print("\n🎉 Все выбранные батчи подготовлены и оптимизированы!")


if __name__ == "__main__":
    main()