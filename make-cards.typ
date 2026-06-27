#let make-cards(cards) = {
  set page(paper: "a4", margin: 8mm)

  show scale: set text(size: 14pt)
//   show align: set block(above: 0.2em, below: 0.2em)

  // Глобальные настройки компактности
  set text(size: 6pt, lang: "ru", hyphenate: true) // Включаем переносы для плотности
  set par(leading: 0.5em, spacing: 0.65em, justify: false)
  set math.equation(block: false) // Пытаемся делать формулы более компактными
  set image(width: 80%) // Картинки по умолчанию не огромные

  let cards-per-page = 9
  let chunks = ()

  for i in range(0, cards.len(), step: cards-per-page) {
    chunks.push(cards.slice(i, calc.min(i + cards-per-page, cards.len())))
  }

  for chunk in chunks {
    // === ЛИЦЕВАЯ СТОРОНА ===
    grid(
      columns: (1fr, 1fr, 1fr),
      rows: (1fr, 1fr, 1fr),
      stroke: 0.5pt + luma(180),
      ..chunk.map(c => block(
        width: 100%, height: 100%, inset: 4pt,
        [
          #align(center)[*#c.title*]
          #v(2pt)
          #c.front
        ]
      ))
    )

    // === ОБРАТНАЯ СТОРОНА ===
    let padded = chunk
    while padded.len() < 9 {
      padded.push((title: "", front: [], back: []))
    }

    let back-items = ()
    for row in range(3) {
      // ИСПРАВЛЕНО: добавили + 3, чтобы забирать по 3 элемента на строку
      let r = padded.slice(row * 3, row * 3 + 3)
      back-items += r.rev()
    }

    grid(
      columns: (1fr, 1fr, 1fr),
      rows: (1fr, 1fr, 1fr),
      stroke: 0.5pt + luma(180),
      ..back-items.map(c => block(
        width: 100%, height: 100%, inset: 4pt,
        if c.title != "" [
          #align(center)[_Пояснения:_ *#c.title*]
          #v(2pt)
//           #set text(size: 5.5pt) // Для пояснений можно еще чуть мельче
          #c.back
        ]
      ))
    )
  }
}