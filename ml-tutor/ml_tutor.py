from typing import Optional, Callable

from anki.cards import Card
from anki.collection import Collection
from anki.scheduler.v3 import QueuedCards
from aqt import mw
from aqt.operations import QueryOp

from .cards_decorators import CardsDecoratorFactory, CardDecoratorBase
from .ml.ml_provider import MLProvider


class MLTutor:
    # todo: refactor into MLTutor and AnkiMLTutor (separate the Anki-specific code)

    def __init__(
        self,
        cards_decorator_factory: CardsDecoratorFactory,
        ml_provider: MLProvider,
        display_original_question: bool = True,
    ):
        self._cards_decorator_factory = cards_decorator_factory
        self._ml_provider = ml_provider
        self._display_original_question = display_original_question

    def set_ml_provider(self, ml_provider: MLProvider):
        self._ml_provider = ml_provider

    def set_display_original_question(self, display_original_question: bool):
        self._display_original_question = display_original_question

    def on_collection_load(self, _: Collection):
        self._start_next_cards_in_queue()

    def on_card_will_show(self, text: str, card: Card, kind: str) -> str:
        decorated_card = self._cards_decorator_factory.decorate_card(
            card=card, display_original_question=self._display_original_question
        )
        if not decorated_card.augmented:
            self._queue_note_augmentation_task(card=decorated_card)
        text = decorated_card.rephrase_text(text=text, kind=kind)
        self._start_next_cards_in_queue()
        return text

    def _start_next_cards_in_queue(self):
        col = mw.col
        next_cards_queue: QueuedCards = col.sched.get_queued_cards(fetch_limit=2)
        for card in next_cards_queue.cards:
            decorate_card = self._cards_decorator_factory.decorate_card(
                card=card.card, display_original_question=self._display_original_question
            )
            self._queue_note_augmentation_task(card=decorate_card)

    def _queue_note_augmentation_task(self, card: CardDecoratorBase):
        op = QueryOp(
            parent=mw,
            op=self._build_note_augmentation_task(card=card),
            success=self._on_task_success,
        )
        op.run_in_background()

    def _build_note_augmentation_task(self, card: CardDecoratorBase) -> Callable:
        def task(_: Collection):
            self._augment_card(card=card)
        return task

    @staticmethod
    def _on_task_success(_: int) -> None:
        pass

    def _augment_card(self, card: CardDecoratorBase):
        card.augment_card(ml_provider=self._ml_provider)
        return 0
