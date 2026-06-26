import os
import re
import cv2
import numpy as np
import pytesseract


# ====================================================================
# ВНИМАНИЕ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ WINDOWS!
# Раскомментируйте строку ниже и укажите правильный путь к tesseract.exe,
# если он установлен не по стандартному пути.
#
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# ====================================================================

def smart_crop(img):
    """Обрезает темный фон, оставляя тетрадь"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (11, 11), 0)
    _, thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)

        margin = 20
        x1 = max(0, x - margin)
        y1 = max(0, y - margin)
        x2 = min(img.shape[1], x + w + margin)
        y2 = min(img.shape[0], y + h + margin)

        return img[y1:y2, x1:x2]
    return img


def manual_rotate(img, filename):
    """Интерактивное окно для ручного поворота"""
    print(f"\n[!] Не удалось автоматически определить ориентацию для файла: {filename}")
    print("Посмотрите на открывшееся окно с картинкой.")

    # Создаем уменьшенную копию картинки, чтобы она поместилась на экран
    h, w = img.shape[:2]
    max_dim = 800
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        display_img = cv2.resize(img, (int(w * scale), int(h * scale)))
    else:
        display_img = img.copy()

    # Показываем изображение
    window_name = f"Rotate: {filename}"
    cv2.imshow(window_name, display_img)
    cv2.waitKey(500)  # Даем системе время прорисовать окно

    # Опрашиваем пользователя в консоли
    print("\nВыберите вариант поворота:")
    print("0 - Не нужно поворачивать (уже правильно)")
    print("1 - Повернуть на 90° ПО часовой стрелке")
    print("2 - Повернуть на 180° (вверх ногами)")
    print("3 - Повернуть на 90° ПРОТИВ часовой стрелки")

    while True:
        choice = input("Введите цифру (0-3) и нажмите Enter: ").strip()
        if choice in ['0', '1', '2', '3']:
            break
        print("Неверный ввод. Пожалуйста, введите число от 0 до 3.")

    # Закрываем окно
    cv2.destroyWindow(window_name)
    cv2.waitKey(1)

    # Поворачиваем согласно выбору
    if choice == '1':
        return cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE), 90
    elif choice == '2':
        return cv2.rotate(img, cv2.ROTATE_180), 180
    elif choice == '3':
        return cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE), 270

    return img, 0


def smart_rotate(img):
    """Пытается автоматически определить ориентацию текста"""
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    try:
        osd_data = pytesseract.image_to_osd(rgb_img, config='--psm 0', output_type=pytesseract.Output.DICT)
        rotate_angle = osd_data['rotate']

        if rotate_angle == 90:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif rotate_angle == 180:
            img = cv2.rotate(img, cv2.ROTATE_180)
        elif rotate_angle == 270:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)

        return img, rotate_angle, True

    except Exception:
        # Возвращаем False третьим параметром, чтобы запустить ручной режим
        return img, 0, False


def process_images(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Создана папка: {output_folder}")

    filename_pattern = re.compile(r"^(photo_\d+).*?(\.[a-zA-Z]+)$")

    for filename in os.listdir(input_folder):
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue

        match = filename_pattern.match(filename)
        new_filename = (match.group(1) + match.group(2)) if match else filename

        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, new_filename)

        print(f"Обработка: {new_filename}...", end=" ", flush=True)

        # 1. Читаем изображение
        img = cv2.imread(input_path)
        if img is None:
            print(" Ошибка чтения файла.")
            continue

        # 2. Обрезаем фон
        cropped_img = smart_crop(img)

        # 3. Умный поворот
        final_img, angle, success = smart_rotate(cropped_img)

        # Если автоматика не справилась, спрашиваем пользователя
        if not success:
            final_img, angle = manual_rotate(cropped_img, new_filename)

        if angle != 0:
            print(f"повернуто на {angle}°...", end=" ", flush=True)

        # 4. Сохраняем
        cv2.imwrite(output_path, final_img)
        print("Готово!")


if __name__ == "__main__":
    INPUT_DIR = ("notes_images_2_src")
    OUTPUT_DIR = "notes_images_2"

    print("Запуск обработки. Скрипт будет работать автоматически, но при необходимости спросит вас.")
    process_images(INPUT_DIR, OUTPUT_DIR)
    print("\nВся обработка завершена!")