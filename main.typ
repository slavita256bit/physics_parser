#import "make-cards.typ": make-cards

#import "Билеты/Билет 01 Электрический заряд и его свойства/ticket.typ": ticket as t01
#import "Билеты/Билет 02 Закон сохранения электрического заряда/ticket.typ": ticket as t02
#import "Билеты/Билет 03 Точечный заряд/ticket.typ": ticket as t03
#import "Билеты/Билет 04 Закон Кулона/ticket.typ": ticket as t04
#import "Билеты/Билет 05 Принцип суперпозиции сил/ticket.typ": ticket as t05
#import "Билеты/Билет 06 Объемная, поверхностная и линейная плотность заряда/ticket.typ": ticket as t06
#import "Билеты/Билет 07 Электростатическое поле/ticket.typ": ticket as t07
#import "Билеты/Билет 08 Напряженность электростатического поля/ticket.typ": ticket as t08
#import "Билеты/Билет 09 Силовые линии электростатического поля/ticket.typ": ticket as t09
#import "Билеты/Билет 10 Напряженность поля точечного заряда и системы зарядов/ticket.typ": ticket as t10
#import "Билеты/Билет 11 Теорема Гаусса для электростатического поля в интегральной и дифференциальной форме/ticket.typ": ticket as t11

// Сборка всех готовых карточек
#make-cards((
  t01,
  t02,
  t03,
  t04,
  t05,
  t06,
  t07,
  t08,
  t09,
  t10,
  t11,
))
