# Класифікатор текстових повідомлень

Локальний вебзастосунок визначає одну категорію короткого україномовного повідомлення. Він підтримує інформаційні запити, повідомлення про збої та пропозиції.

## Запуск на Windows 11

Потрібні Python 3.13, Node.js 24 і pnpm 11. Команди нижче виконуються в PowerShell із папки проєкту.

~~~
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

Set-Location frontend
pnpm install --frozen-lockfile
pnpm run build
Set-Location ..

.\.venv\Scripts\python.exe -m app.setup --seed
.\.venv\Scripts\python.exe -m app.training
.\.venv\Scripts\python.exe -m app.users reviewer maintainer
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
~~~

Команда створення облікового запису двічі запитує пароль. Введіть щонайменше 15 символів. Після запуску відкрийте [вебінтерфейс](http://127.0.0.1:8000/) і ввійдіть як reviewer. [Документація API](http://127.0.0.1:8000/docs) працює з того самого локального сервера.

| Роль | Можливості |
| --- | --- |
| operator | Класифікувати повідомлення |
| coordinator | Переглядати зведення |
| maintainer | Класифікувати, переглядати зведення та керувати прикладами |

Для окремих облікових записів використовуйте команду app.users з іншим логіном і потрібною роллю. Фахівець із супроводу також може запустити навчання з PowerShell.

## Дані та модель

Команда setup --seed додає 72 розмічені приклади до порожньої бази й розподіляє їх між навчальною та перевірною вибірками. Розмічені тексти зберігаються в runtime/classifier.sqlite3. Файл database/classification_demo.sqlite3 містить дані для лабораторної № 5.

Навчання використовує TfidfVectorizer і MultinomialNB. Воно зберігає model.joblib та statistics.json в одному каталозі всередині runtime/artifacts. Після нового навчання перезапустіть сервер, щоб завантажити активну модель і відповідне зведення.

За замовчуванням використовується стратегія multinomial. Щоб навчити ComplementNB на тих самих вибірках, виконайте таку команду PowerShell.

~~~
.\.venv\Scripts\python.exe -m app.training --strategy complement
~~~

Зведення statistics.json фіксує обрану стратегію та результат оцінювання.

Уведений у форму класифікації текст обробляється в пам’яті. До бази записуються розмічені приклади, які фахівець додає окремою дією. Використані під час оцінювання приклади позначено в списку й захищено від зміни та видалення.

## Перевірка

~~~
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
~~~

Окремо можна переглянути прототип з лабораторних № 6–7. Виконайте pnpm run dev у папці frontend та відкрийте адресу [Vite](http://127.0.0.1:5173/). У цьому режимі використовуються тимчасові демонстраційні дані.
