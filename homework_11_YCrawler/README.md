## Ycrawler

### Цель скрипта:
Асинхронный парсинг новостного сайта

### Результат:
Происходит обкачка новостей с корня сайта "news.ycombinator.com".
Далее идёт просмотр комментов по каждой новости и скрабинг ссылок из них.
Содержимое этих ссылок сохраняется в файл данной новости.
Весь скрабинг происходит асинхронно.

### Основная функциональность:
1. `main.py` - файл парсинга

### Мониторинг:
1. Логи основной программы пишутся в `logs.log`

### Аналитика:
1. Среднее время одного цикла обкачки - 45 сек


### Инструкции по запуску:
0. Устанавливать внешних зависимостей:
`pip instal -r requirments.txt`

- Запуск основной программы: 
1. `cd <Абсолютный путь к директории homework_9_MemcLoad>`
2. `python main.py`
