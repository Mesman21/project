from typing import Protocol

from sklearn.base import BaseEstimator
from sklearn.naive_bayes import ComplementNB, MultinomialNB


class TrainingStrategy(Protocol):
    @property
    def name(self) -> str: ...

    def build_estimator(self) -> BaseEstimator: ...


class MultinomialStrategy:
    name = "multinomial"

    def build_estimator(self) -> MultinomialNB:
        return MultinomialNB()


class ComplementStrategy:
    name = "complement"

    def build_estimator(self) -> ComplementNB:
        return ComplementNB()


DEFAULT_STRATEGY = MultinomialStrategy()
STRATEGIES: dict[str, TrainingStrategy] = {
    strategy.name: strategy
    for strategy in (DEFAULT_STRATEGY, ComplementStrategy())
}
