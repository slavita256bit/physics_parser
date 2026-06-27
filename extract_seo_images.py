import os
import glob
import fitz  # PyMuPDF


def extract_images_from_pdf(pdf_path, output_dir):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Не удалось открыть {pdf_path}: {e}")
        return 0

    img_count = 0
    for page_idx in range(len(doc)):
        page = doc[page_idx]

        # Получаем информацию обо всех изображениях на странице, включая их координаты (bbox)
        image_infos = page.get_image_info()

        for img_info in image_infos:
            bbox = img_info["bbox"]
            rect = fitz.Rect(bbox)

            # Фильтруем мелкий мусор (логотипы, маркеры списков) меньше 100x100 пикселей
            if rect.width < 100 or rect.height < 100:
                continue

            # Добавляем небольшие поля (по 15 пикселей), чтобы гарантированно
            # захватить формулы-подписи, которые могут слегка вылезать за границы картинки
            rect.x0 = max(0, rect.x0 - 15)
            rect.y0 = max(0, rect.y0 - 15)
            rect.x1 = min(page.rect.width, rect.x1 + 15)
            rect.y1 = min(page.rect.height, rect.y1 + 15)

            img_count += 1
            img_name = f"seo_img_p{page_idx + 1}_{img_count}.png"
            img_path = os.path.join(output_dir, img_name)

            try:
                # ВАЖНО: Мы не извлекаем картинку, а РЕНДЕРИМ этот участок страницы.
                # Это объединяет фоновый белый лист, линии и текстовые формулы в единый PNG!
                # dpi=300 дает превосходную четкость для печати
                pix = page.get_pixmap(clip=rect, dpi=300)
                pix.save(img_path)
            except Exception as e:
                print(f"Ошибка при рендере области на стр. {page_idx + 1}: {e}")

    doc.close()
    return img_count


def main():
    base_dir = "Билеты"

    if not os.path.exists(base_dir):
        print(f"Папка '{base_dir}' не найдена! Запустите сначала скрипт нарезки билетов.")
        return

    ticket_dirs = sorted(glob.glob(os.path.join(base_dir, "Билет *")))
    total_images = 0

    print("--- Сверхточный рендеринг схем из СЭО (слияние слоев и текста) ---")

    for ticket_dir in ticket_dirs:
        seo_pdf_path = os.path.join(ticket_dir, "seo_extract.pdf")

        if os.path.exists(seo_pdf_path):
            count = extract_images_from_pdf(seo_pdf_path, ticket_dir)
            if count > 0:
                print(f"[{os.path.basename(ticket_dir)}]: Успешно извлечено схем: {count}")
                total_images += count

    print(f"\nГотово! Всего сохранено {total_images} схем высокого разрешения.")


if __name__ == "__main__":
    main()