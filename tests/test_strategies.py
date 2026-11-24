from sklearn.naive_bayes import ComplementNB, MultinomialNB

from app.strategies import STRATEGIES
from app.training import build_pipeline


def test_default_pipeline_keeps_multinomial_nb() -> None:
    first = build_pipeline().named_steps["classifier"]
    second = build_pipeline().named_steps["classifier"]

    assert isinstance(first, MultinomialNB)
    assert first is not second


def test_complement_strategy_trains_with_shared_vectorizer() -> None:
    pipeline = build_pipeline(STRATEGIES["complement"])
    messages = [
        "Де розклад занять?",
        "Де знайти матеріали?",
        "Помилка під час входу.",
        "Помилка під час збереження.",
    ]
    labels = ["information_request"] * 2 + ["incident_report"] * 2
    pipeline.fit(messages, labels)

    assert isinstance(pipeline.named_steps["classifier"], ComplementNB)
    assert pipeline.predict(["Де розклад занять?"])[0] == "information_request"
