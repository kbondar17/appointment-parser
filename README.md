# appointment-parser
Это парсер указов о назначениях и отставках российских чиновников, которые публикуются на официальном портале правовой информации http://pravo.gov.ru/. 

## Команды
Распарсить файл

```python -m parse file --file '123456789.html' --result 'parsed.json'```

Распарсить все файлы в директории

```python -m parse folder --folder './decree_data' --destination-folder './parsed_results'```