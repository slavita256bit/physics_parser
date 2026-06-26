import os
import json
import glob
import re
from pypdf import PdfReader, PdfWriter
from PIL import Image


def clean_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)


def merge_json_configs(config_dir):
    # Находит все .json файлы в папке config_dir и склеивает их в один словарь
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
    output_dir = "Билеты"

    print("--- Старт пайплайна разделения ---")

    # Объединяем все конфигурационные файлы
    config = merge_json_configs(config_dir)
    if not config:
        print(f"Ошибка! В папке '{config_dir}' не найдено файлов конфигурации .json.")
        return

    # Открываем тяжелые файлы один раз
    notes_reader = PdfReader(notes_pdf_path) if os.path.exists(notes_pdf_path) else None
    sav2_reader = PdfReader(saveliev_2_path) if os.path.exists(saveliev_2_path) else None
    sav3_reader = PdfReader(saveliev_3_path) if os.path.exists(saveliev_3_path) else None

    # Буфер ридеров для документов СЭО (чтобы не открывать по сто раз)
    seo_readers = {}

    for ticket_num, t_data in config.items():
        t_num_int = int(ticket_num)
        title = t_data.get("title", f"Билет_{t_num_int}")
        folder_name = f"Билет {t_num_int:02d} {clean_filename(title)}"
        ticket_path = os.path.join(output_dir, folder_name)
        os.makedirs(ticket_path, exist_ok=True)

        print(f"Обработка билета {t_num_int:02d}: {title}...")

        # 1. Обработка рукописных заметок (notes_pdf)
        notes_pages = t_data.get("notes_pdf", [])
        if notes_pages and notes_reader:
            writer = PdfWriter()
            for p in notes_pages:
                if p - 1 < len(notes_reader.pages):
                    writer.add_page(notes_reader.pages[p - 1])
            with open(os.path.join(ticket_path, "my_notes.pdf"), "wb") as f:
                writer.write(f)

        # 2. Обработка фотографий конспектов (notes_images) -> конвертация в PDF
        img_names = t_data.get("notes_images", [])
        if img_names:
            img_paths = [os.path.join("notes_images", img) for img in img_names if
                         os.path.exists(os.path.join("notes_images", img))]
            if img_paths:
                images = [Image.open(img).convert("RGB") for img in img_paths]
                images[0].save(os.path.join(ticket_path, "my_notes_images.pdf"), save_all=True,
                               append_images=images[1:])

        # 3. Вырезка страниц из конкретного PDF СЭО (seo_pdf + seo_pages)
        seo_filename = t_data.get("seo_pdf")
        seo_pages = t_data.get("seo_pages", [])
        if seo_filename and seo_pages:
            seo_filepath = os.path.join(seo_folder, seo_filename)
            if not os.path.exists(seo_filepath):
                print(f"{seo_filepath} does not exist")
                return

            if seo_filename not in seo_readers:
                seo_readers[seo_filename] = PdfReader(seo_filepath)

            reader = seo_readers[seo_filename]
            writer = PdfWriter()
            for p in seo_pages:
                if p - 1 < len(reader.pages):
                    writer.add_page(reader.pages[p - 1])
            with open(os.path.join(ticket_path, "seo_extract.pdf"), "wb") as f:
                writer.write(f)

        # 4. Вырезка страниц из Савельева (sav_vol + sav_pages)
        sav_vol = t_data.get("sav_vol")
        sav_pages = t_data.get("sav_pages", [])
        if sav_vol and sav_pages:
            reader = sav2_reader if sav_vol == 2 else sav3_reader
            if reader:
                writer = PdfWriter()
                for p in sav_pages:
                    if p < len(reader.pages):
                        if sav_vol == 2:
                            offset = 10
                        else:
                            offset = 0
                        writer.add_page(reader.pages[p + offset])
                with open(os.path.join(ticket_path, f"saveliev_vol{sav_vol}_extract.pdf"), "wb") as f:
                    writer.write(f)

    print(f"\nУспешно обработано билетов: {len(config)}. Результаты в папке '{output_dir}'.")


if __name__ == "__main__":
    main()