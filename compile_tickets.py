import os
import subprocess
import sys

# Настройка путей
TICKETS_DIR = "Билеты"
TYPST_BIN = "typst"  # Убедитесь, что typst установлен в системе и доступен в PATH

# Шаблон обертки для генерации красивой карточки (Лицевая сторона)
FRONT_WRAPPER = """
#import "{ticket_file}": ticket
#set page(width: 12cm, height: auto, margin: 0pt, fill: none)
#set text(font: "Inter", size: 11pt, fill: rgb("0f172a"))

#box(
  width: 100%,
  inset: 20pt,
  radius: 12pt,
  fill: rgb("ffffff"),
  stroke: 1pt + rgb("e2e8f0"),
  [
    #if "title" in ticket [
      #align(center)[*#ticket.title*]
      #v(8pt)
      #line(length: 100%, stroke: 0.5pt + rgb("cbd5e1"))
      #v(8pt)
    ]
    #ticket.front
  ]
)
"""

# Шаблон обертки для обратной стороны
BACK_WRAPPER = """
#import "{ticket_file}": ticket
#set page(width: 12cm, height: auto, margin: 0pt, fill: none)
#set text(font: "Inter", size: 11pt, fill: rgb("0f172a"))

#box(
  width: 100%,
  inset: 20pt,
  radius: 12pt,
  fill: rgb("ffffff"),
  stroke: 1pt + rgb("e2e8f0"),
  [
    #if "title" in ticket [
      #align(center)[*#ticket.title*]
      #v(8pt)
      #line(length: 100%, stroke: 0.5pt + rgb("cbd5e1"))
      #v(8pt)
    ]
    #ticket.back
  ]
)
"""


def compile_ticket(root, file):
    ticket_path = os.path.join(root, file)
    print(f"Обработка {ticket_path}...")

    front_typ = os.path.join(root, "_front_wrapper.typ")
    back_typ = os.path.join(root, "_back_wrapper.typ")

    front_svg = os.path.join(root, "front.svg")
    back_svg = os.path.join(root, "back.svg")

    try:
        # Создаем временные typst файлы для рендера
        with open(front_typ, "w", encoding="utf-8") as f:
            f.write(FRONT_WRAPPER.replace("{ticket_file}", file))

        with open(back_typ, "w", encoding="utf-8") as f:
            f.write(BACK_WRAPPER.replace("{ticket_file}", file))

        # Компилируем front
        res_front = subprocess.run([TYPST_BIN, "compile", front_typ, front_svg], capture_output=True, text=True)
        if res_front.returncode == 0:
            print(f"  [+] Успешно: {front_svg}")
        else:
            print(f"  [-] Ошибка компиляции front:\\n{res_front.stderr}")
            if os.path.exists(front_svg): os.remove(front_svg)

        # Компилируем back
        res_back = subprocess.run([TYPST_BIN, "compile", back_typ, back_svg], capture_output=True, text=True)
        if res_back.returncode == 0:
            print(f"  [+] Успешно: {back_svg}")
        else:
            print(f"  [-] Ошибка компиляции back:\\n{res_back.stderr}")
            if os.path.exists(back_svg): os.remove(back_svg)

    except Exception as e:
        print(f"  [!] Ошибка при обработке {ticket_path}: {e}")
    finally:
        # Удаляем временные файлы
        if os.path.exists(front_typ):
            os.remove(front_typ)
        if os.path.exists(back_typ):
            os.remove(back_typ)


def main():
    if not os.path.exists(TICKETS_DIR):
        print(f"Папка {TICKETS_DIR} не найдена.")
        return

    for root, dirs, files in os.walk(TICKETS_DIR):
        for file in files:
            if file == "ticket.typ":
                compile_ticket(root, file)


if __name__ == "__main__":
    main()
