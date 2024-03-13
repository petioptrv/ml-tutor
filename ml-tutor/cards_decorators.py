import inspect
from abc import ABC, abstractmethod, ABCMeta
from threading import Event
from typing import Union

from anki.cards import Card, CardId
from aqt import mw
from bs4 import BeautifulSoup

from anki.notes import Note
from .constants import (
    LLM_NORMAL_CARD_REPHRASING_FRONT_PROMPT,
    TUTOR_NAME,
    CARD_TEXT_PARSER,
    LLM_NORMAL_CARD_REPHRASING_BACK_PROMPT,
)
from .ml.ml_provider import MLProvider


class CardsDecoratorFactory:
    @staticmethod
    def decorate_card(card: Card, display_original_question: bool) -> "CardDecoratorBase":
        col = mw.col
        model_name = col.models.get(
            col.get_note(id=col.get_card(id=card.id).nid).mid
        )["name"].lower()

        decorator_cls = CardDecoratorBase.registry.get(model_name)
        if decorator_cls is None:
            decorator_cls = PassThroughCardDecorator

        decorated_card = decorator_cls(card, display_original_question)

        return decorated_card


class DecoratorRegistry(type):
    def __init__(cls, name, bases, clsdict):
        if not hasattr(cls, "registry"):
            cls.registry = {}
        if inspect.isabstract(cls) is False and hasattr(cls, "get_model_name"):
            model_name = cls.get_model_name()
            cls.registry[model_name.lower()] = cls
        super().__init__(name, bases, clsdict)


class DecoratorRegistryMeta(ABCMeta, DecoratorRegistry):
    pass


class CardDecoratorBase(ABC, metaclass=DecoratorRegistryMeta):
    def __init__(self, card: Card, display_original_question: bool):
        self._card = card
        self._display_original_question = display_original_question

    @property
    def id(self) -> Union[CardId, None]:
        return self._card.id

    @property
    @abstractmethod
    def augmented(self) -> bool:
        ...

    @staticmethod
    @abstractmethod
    def get_model_name() -> str:
        ...

    @abstractmethod
    def augment_card(self, ml_provider: MLProvider):
        ...

    @abstractmethod
    def rephrase_text(self, text: str, kind: str) -> str:
        ...

    def get_card_note(self) -> Note:
        col = mw.col
        note = col.get_note(id=col.get_card(id=self.id).nid)
        return note


class PassThroughCardDecorator(CardDecoratorBase):
    @property
    def augmented(self) -> bool:
        return True

    @staticmethod
    def get_model_name() -> str:
        return ""

    def augment_card(self, ml_provider: MLProvider):
        pass

    def rephrase_text(self, text: str, kind: str) -> str:
        return text


class BasicCardDecoratorBase(CardDecoratorBase, ABC):
    # todo: handle when there are extra fields in the note

    def __init__(self, card: Card, display_original_question: bool):
        super().__init__(card=card, display_original_question=display_original_question)
        self._augmented_event = Event()

    def augment_card(self, ml_provider: MLProvider):
        self._augment_front(ml_provider=ml_provider)
        self._augment_back(ml_provider=ml_provider)
        self._augmented_event.set()

    def rephrase_text(self, text: str, kind: str) -> str:
        if not self.augmented:
            self._augmented_event.wait()
        augmented_text = self._augment_card_text_question(text=text)
        if kind == "reviewAnswer" and self._display_original_question:
            augmented_text = self._augment_card_text_answer(text=augmented_text)
        return augmented_text

    @abstractmethod
    def _augment_front(self, ml_provider: MLProvider):
        ...

    @abstractmethod
    def _augment_back(self, ml_provider: MLProvider):
        ...

    @abstractmethod
    def _get_rephrased_question_from_original_question(self, question: str) -> str:
        ...

    @abstractmethod
    def _get_original_question_from_original_card_text(self, text: str) -> str:
        ...

    @abstractmethod
    def _get_original_question_from_augmented_card_text(self, text: str) -> str:
        ...

    def _augment_card_text_question(self, text: str) -> str:
        soup = BeautifulSoup(markup=text, features=CARD_TEXT_PARSER)
        first_span = soup.find("span")
        if first_span is not None:
            question = first_span.string
            rephrased_question = self._get_rephrased_question_from_original_question(question=question)
            first_span.string = rephrased_question
            text = str(soup)
        else:
            question = self._get_original_question_from_original_card_text(text=text)
            rephrased_question = self._get_rephrased_question_from_original_question(
                question=question
            )
            text = text.replace(question, rephrased_question, 1)
        return text

    def _augment_card_text_answer(self, text: str) -> str:
        soup = BeautifulSoup(markup=text, features=CARD_TEXT_PARSER)

        # Create a new <hr> tag
        hr_tag = soup.new_tag("hr")
        hr_tag['id'] = "original-question"
        soup.body.append(hr_tag)

        bold_tag = soup.new_tag("b")
        bold_tag.string = f"[{TUTOR_NAME}] Original Question"
        p_tag = soup.new_tag("p")
        p_tag.append(bold_tag)
        soup.body.append(p_tag)

        original_question = self._get_original_question_from_augmented_card_text(text=text)
        original_question_soup = BeautifulSoup(markup=original_question, features=CARD_TEXT_PARSER)
        original_question_span = original_question_soup.find("span")

        if original_question_span is None:
            original_question_span = soup.new_tag("span")
            original_question_span.string = original_question

        soup.body.append(original_question_span)

        modified_html = str(soup)
        return modified_html


class BasicCardDecorator(BasicCardDecoratorBase):
    _rephrased_fronts = {}

    def __init__(self, card: Card, display_original_question: bool):
        super().__init__(card=card, display_original_question=display_original_question)
        self._rephrased_front = self._rephrased_fronts.get(card.id)

    @property
    def augmented(self) -> bool:
        return self._rephrased_front is not None

    @staticmethod
    def get_model_name() -> str:
        return "basic"

    def _augment_front(self, ml_provider: MLProvider):
        if self._rephrased_front is None:
            self._rephrased_front = self._generate_rephrased_front(ml_provider=ml_provider)
            self._rephrased_fronts[self.id] = self._rephrased_front

    def _generate_rephrased_front(self, ml_provider: MLProvider) -> str:
        front = self._extract_card_front()
        prompt = LLM_NORMAL_CARD_REPHRASING_FRONT_PROMPT.format(card_text=front)
        rephrased_front = ml_provider.completion(prompt=prompt)
        rephrased_front = rephrased_front.strip('"').strip("'")
        if len(rephrased_front) == 0:
            rephrased_front = f"{front}<br><br><b>[{TUTOR_NAME}]</b> Failed to rephrase card front due to ambiguity."
        return rephrased_front

    def _augment_back(self, ml_provider: MLProvider):
        pass

    def _get_rephrased_question_from_original_question(self, question: str) -> str:
        return self._rephrased_front

    def _get_original_question_from_original_card_text(self, text: str) -> str:
        return self._extract_card_front()

    def _get_original_question_from_augmented_card_text(self, text: str) -> str:
        return self._extract_card_front()

    def _extract_card_front(self) -> str:
        note = self.get_card_note()
        front = note["Front"]
        return front


class BasicAndReverseCardDecorator(BasicCardDecorator):
    _rephrased_backs = {}

    def __init__(self, card: Card, display_original_question: bool):
        super().__init__(card=card, display_original_question=display_original_question)
        self._rephrased_back = self._rephrased_backs.get(card.id)

    @property
    def augmented(self) -> bool:
        return super().augmented and self._rephrased_back is not None

    @staticmethod
    def get_model_name() -> str:
        return "basic (and reversed card)"

    def _augment_back(self, ml_provider: MLProvider):
        if self._rephrased_back is None:
            self._rephrased_back = self._generate_rephrased_back(
                ml_provider=ml_provider
            )
            self._rephrased_backs[self.id] = self._rephrased_back

    def _get_rephrased_question_from_original_question(self, question: str) -> str:
        front_string = self._extract_card_front_string()
        if question == front_string:
            rephrased_question = self._rephrased_front
        else:
            rephrased_question = self._rephrased_back
        return rephrased_question

    def _extract_card_front_string(self) -> str:
        front = self._extract_card_front()
        soup = BeautifulSoup(markup=front, features=CARD_TEXT_PARSER)
        span = soup.find("span")
        if span is not None:
            front_string = span.string
        else:
            front_string = front
        return front_string

    def _get_original_question_from_original_card_text(self, text: str) -> str:
        question_string = self._find_first_match_in_string(
            target=text, first_sub=self._extract_card_front(), second_sub=self._extract_card_back()
        )
        return question_string

    def _get_original_question_from_augmented_card_text(self, text: str) -> str:
        rephrased_question = self._find_first_match_in_string(
            target=text, first_sub=self._rephrased_front, second_sub=self._rephrased_back
        )
        if rephrased_question == self._rephrased_front:
            original_question = self._extract_card_front()
        else:
            original_question = self._extract_card_back()
        return original_question

    @staticmethod
    def _find_first_match_in_string(target: str, first_sub: str, second_sub: str):
        first_index = target.find(first_sub)
        second_index = target.find(second_sub)
        if first_index < 0:
            match = second_sub
        elif second_index < 0:
            match = first_sub
        elif first_index < second_index:
            match = first_sub
        elif first_index > second_index:
            match = second_sub
        elif len(first_sub) < len(second_sub):
            match = second_sub
        else:
            match = first_sub
        return match

    def _generate_rephrased_back(self, ml_provider: MLProvider) -> str:
        back = self._extract_card_back()
        prompt = LLM_NORMAL_CARD_REPHRASING_BACK_PROMPT.format(card_text=back)
        rephrased_back = ml_provider.completion(prompt=prompt)
        rephrased_back = rephrased_back.strip('"').strip("'")
        if len(rephrased_back) == 0:
            rephrased_back = f"{back}<br><br><b>[{TUTOR_NAME}]</b> Failed to rephrase card back due to ambiguity."
        return rephrased_back

    def _extract_card_back(self) -> str:
        note = self.get_card_note()
        back = note["Back"]
        return back


class ClozeCardDecorator(CardDecoratorBase):
    @property
    def augmented(self) -> bool:
        raise NotImplementedError

    @staticmethod
    def get_model_name() -> str:
        return "cloze"

    def augment_card(self, ml_provider: MLProvider):
        raise NotImplementedError

    def rephrase_text(self, text: str, kind: str) -> str:
        raise NotImplementedError
