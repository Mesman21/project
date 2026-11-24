-- Вигадані повідомлення та задані вручну прогнози для перевірки схеми.
PRAGMA foreign_keys = ON;

BEGIN;

INSERT INTO categories (category_code, category_name) VALUES
    ('information_request', 'Інформаційний запит'),
    ('incident_report', 'Повідомлення про збій'),
    ('suggestion', 'Пропозиція');

INSERT INTO labeled_messages (message_id, text, category_code, dataset_split) VALUES
    (1, 'Де знайти перелік матеріалів курсу?', 'information_request', 'train'),
    (2, 'Коли відбудеться наступна консультація?', 'information_request', 'train'),
    (3, 'Після оновлення не відкривається сторінка профілю.', 'incident_report', 'train'),
    (4, 'Під час завантаження файла з’являється помилка.', 'incident_report', 'train'),
    (5, 'Додайте пошук за назвою розділу.', 'suggestion', 'train'),
    (6, 'Пропоную додати нагадування за день до події.', 'suggestion', 'train'),
    (7, 'Де можна переглянути розклад занять?', 'information_request', 'test'),
    (8, 'Які документи потрібні для реєстрації?', 'information_request', 'test'),
    (9, 'Після входу сторінка залишається порожньою.', 'incident_report', 'test'),
    (10, 'Було б зручно отримувати сповіщення про зміни розкладу.', 'suggestion', 'test');

INSERT INTO evaluation_runs (evaluation_id, model_version, created_at) VALUES
    (1, 'demo-v1', '2026-11-24 00:00:00');

INSERT INTO predictions (evaluation_id, message_id, predicted_category_code) VALUES
    (1, 7, 'information_request'),
    (1, 8, 'information_request'),
    (1, 9, 'incident_report'),
    (1, 10, 'incident_report');

COMMIT;
