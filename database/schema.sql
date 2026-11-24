PRAGMA foreign_keys = ON;

BEGIN;

CREATE TABLE categories (
    category_code TEXT PRIMARY KEY CHECK (
        length(category_code) BETWEEN 1 AND 48
        AND category_code GLOB '[a-z]*'
        AND category_code NOT GLOB '*[^a-z0-9_]*'
    ),
    category_name TEXT NOT NULL UNIQUE CHECK (length(trim(category_name)) > 0)
) STRICT;

CREATE TABLE labeled_messages (
    message_id INTEGER PRIMARY KEY,
    text TEXT NOT NULL UNIQUE CHECK (
        length(text) BETWEEN 1 AND 2000
        AND instr(text, char(0)) = 0
        AND text = trim(text, char(
            9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760,
            8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200, 8201,
            8202, 8232, 8233, 8239, 8287, 12288
        ))
    ),
    category_code TEXT NOT NULL REFERENCES categories (category_code),
    dataset_split TEXT NOT NULL CHECK (dataset_split IN ('train', 'test'))
) STRICT;

CREATE TABLE evaluation_runs (
    evaluation_id INTEGER PRIMARY KEY,
    model_version TEXT NOT NULL CHECK (length(trim(model_version)) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
) STRICT;

CREATE TABLE predictions (
    evaluation_id INTEGER NOT NULL
        REFERENCES evaluation_runs (evaluation_id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL REFERENCES labeled_messages (message_id),
    predicted_category_code TEXT NOT NULL REFERENCES categories (category_code),
    PRIMARY KEY (evaluation_id, message_id)
) STRICT;

CREATE INDEX predictions_by_message ON predictions (message_id);

CREATE TRIGGER require_test_message_on_prediction_insert
BEFORE INSERT ON predictions
WHEN EXISTS (
    SELECT 1
    FROM labeled_messages
    WHERE message_id = NEW.message_id AND dataset_split <> 'test'
)
BEGIN
    SELECT RAISE(ABORT, 'Прогноз має посилатися на перевірний приклад');
END;

CREATE TRIGGER require_test_message_on_prediction_update
BEFORE UPDATE OF message_id ON predictions
WHEN EXISTS (
    SELECT 1
    FROM labeled_messages
    WHERE message_id = NEW.message_id AND dataset_split <> 'test'
)
BEGIN
    SELECT RAISE(ABORT, 'Прогноз має посилатися на перевірний приклад');
END;

-- Пов’язані з оцінюванням дані визначають еталон для обчислення метрик.
CREATE TRIGGER protect_evaluated_message
BEFORE UPDATE OF text, category_code, dataset_split ON labeled_messages
WHEN (
    NEW.text <> OLD.text
    OR NEW.category_code <> OLD.category_code
    OR NEW.dataset_split <> OLD.dataset_split
) AND EXISTS (
    SELECT 1 FROM predictions WHERE message_id = OLD.message_id
)
BEGIN
    SELECT RAISE(ABORT, 'Приклад уже використано для оцінювання');
END;

CREATE VIEW evaluation_totals AS
SELECT
    p.evaluation_id,
    COUNT(*) AS total,
    SUM(p.predicted_category_code = m.category_code) AS correct,
    AVG(p.predicted_category_code = m.category_code) AS accuracy
FROM predictions AS p
JOIN labeled_messages AS m USING (message_id)
GROUP BY p.evaluation_id;

CREATE VIEW evaluation_distribution AS
SELECT
    t.evaluation_id,
    c.category_code,
    c.category_name,
    COUNT(p.message_id) AS count,
    1.0 * COUNT(p.message_id) / t.total AS share
FROM evaluation_totals AS t
CROSS JOIN categories AS c
LEFT JOIN predictions AS p
    ON p.evaluation_id = t.evaluation_id
    AND p.predicted_category_code = c.category_code
GROUP BY t.evaluation_id, c.category_code, c.category_name, t.total;

COMMIT;
