import inspect
import re
from abc import ABC, abstractmethod, ABCMeta
from threading import Event
from typing import Union, Optional, Dict

from anki.notes_pb2 import Note
from aqt import mw
from aqt.operations import QueryOp
from bs4 import BeautifulSoup

from .persistent_structures import PersistentDict
from .utils import Singleton
from .constants import (
    LLM_NORMAL_NOTE_REPHRASING_FRONT_PROMPT,
    TUTOR_NAME,
    NOTE_TEXT_PARSER,
    LLM_NORMAL_NOTE_REPHRASING_BACK_PROMPT,
    LLM_CLOZE_NOTE_REPHRASING_PROMPT,
    CLOZE_DATA_FILE_NAME,
)
from .ml.ml_provider import MLProvider


class NotesWrapperFactory(metaclass=Singleton):
    _note_wrappers: Dict[int, "NoteWrapperBase"] = {}

    @classmethod
    def get_wrapped_note(
        cls, note: Note, display_original_question: Optional[bool] = None
    ) -> "NoteWrapperBase":
        if note.id in NotesWrapperFactory._note_wrappers:
            wrapped_note = NotesWrapperFactory._note_wrappers[note.id]
            if display_original_question is not None:
                wrapped_note.set_display_original_question(display_original_question=display_original_question)
        else:
            col = mw.col
            model_name = col.models.get(col.get_note(id=note.id).mid)["name"].lower()

            decorator_cls = NoteWrapperBase.registry.get(model_name)
            if decorator_cls is None:
                decorator_cls = PassThroughNoteWrapper

            display_original_question = display_original_question is None or display_original_question
            wrapped_note = decorator_cls(note, display_original_question)

            NotesWrapperFactory._note_wrappers[note.id] = wrapped_note

        return wrapped_note


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


class NoteWrapperBase(ABC, metaclass=DecoratorRegistryMeta):  # todo: rename decorator to something else
    @property
    @abstractmethod
    def rephrased(self) -> bool:  # todo: rename "augmented" to "rephrased"
        ...

    @staticmethod
    @abstractmethod
    def get_model_name() -> str:
        ...

    @abstractmethod
    def rephrase_text(self, text: str, kind: str) -> str:
        ...

    @abstractmethod
    def _do_rephrase_note(self, ml_provider: MLProvider):
        ...

    @abstractmethod
    def _do_restore_note(self):
        """Notes should be able to be restored even after Anki restart."""
        ...

    def __init__(self, note: Note, display_original_question: bool):
        self._note_id = note.id
        self._display_original_question = display_original_question
        self._is_rephrasing: Optional[Event] = None
        self._is_restoring: Optional[Event] = None

    @property
    def id(self) -> Union[int, None]:
        return self.get_note().id

    def get_note(self) -> Note:
        return mw.col.get_note(id=self._note_id)

    def set_display_original_question(self, display_original_question: bool):
        self._display_original_question = display_original_question

    def rephrase_note(self, ml_provider: MLProvider):
        self.wait_restoration()
        self.wait_rephrasing()
        self._is_rephrasing = Event()
        op = QueryOp(
            parent=mw,
            op=lambda _: self._do_rephrase(ml_provider=ml_provider),
            success=lambda _: _,
        )
        op.run_in_background()

    def restore_note(self):
        self.wait_rephrasing()
        self.wait_restoration()
        self._is_restoring = Event()
        op = QueryOp(
            parent=mw,
            op=lambda _: self._do_restore(),
            success=lambda _: _,
        )
        op.run_in_background()

    def wait_rephrasing(self):
        self._is_rephrasing and self._is_rephrasing.wait()

    def wait_restoration(self):
        self._is_restoring and self._is_restoring.wait()

    def _do_rephrase(self, ml_provider: MLProvider) -> int:
        self._do_rephrase_note(ml_provider=ml_provider)
        is_augmenting = self._is_rephrasing
        self._is_rephrasing = None
        is_augmenting.set()
        return 0

    def _do_restore(self) -> int:
        self._do_restore_note()
        is_restoring = self._is_restoring
        self._is_restoring = None
        is_restoring.set()
        return 0


class PassThroughNoteWrapper(NoteWrapperBase):
    @property
    def rephrased(self) -> bool:
        return True

    @staticmethod
    def get_model_name() -> str:
        return ""

    def rephrase_text(self, text: str, kind: str) -> str:
        return text

    def _do_rephrase_note(self, ml_provider: MLProvider):
        pass

    def _do_restore_note(self):
        pass


class BasicNoteWrapperBase(NoteWrapperBase, ABC):
    @abstractmethod
    def _get_rephrased_question_from_original_question(self, question: str) -> str:
        ...

    @abstractmethod
    def _get_original_question_from_original_note_text(self, text: str) -> str:
        ...

    @abstractmethod
    def _get_original_question_from_augmented_note_text(self, text: str) -> str:
        ...

    def rephrase_text(self, text: str, kind: str) -> str:
        augmented_text = self._rephrase_note_text_question(text=text)
        if kind == "reviewAnswer" and self._display_original_question:
            augmented_text = self._rephrase_note_text_answer(text=augmented_text)
        return augmented_text

    def _rephrase_note_text_question(self, text: str) -> str:
        soup = BeautifulSoup(markup=text, features=NOTE_TEXT_PARSER)
        first_span = soup.find("span")
        if first_span is not None:
            question = first_span.string
            rephrased_question = self._get_rephrased_question_from_original_question(question=question)
            first_span.string = rephrased_question
            text = str(soup)
        else:
            question = self._get_original_question_from_original_note_text(text=text)
            rephrased_question = self._get_rephrased_question_from_original_question(
                question=question
            )
            text = text.replace(question, rephrased_question, 1)
        return text

    def _rephrase_note_text_answer(self, text: str) -> str:
        soup = BeautifulSoup(markup=text, features=NOTE_TEXT_PARSER)

        # Create a new <hr> tag
        hr_tag = soup.new_tag("hr")
        hr_tag['id'] = "original-question"
        soup.body.append(hr_tag)

        bold_tag = soup.new_tag("b")
        bold_tag.string = f"[{TUTOR_NAME}] Original Question"
        p_tag = soup.new_tag("p")
        p_tag.append(bold_tag)
        soup.body.append(p_tag)

        original_question = self._get_original_question_from_augmented_note_text(text=text)
        original_question_soup = BeautifulSoup(markup=original_question, features=NOTE_TEXT_PARSER)
        original_question_span = original_question_soup.find("span")

        if original_question_span is None:
            original_question_span = soup.new_tag("span")
            original_question_span.string = original_question

        soup.body.append(original_question_span)

        modified_html = str(soup)
        return modified_html


class BasicNoteWrapper(BasicNoteWrapperBase):
    _rephrased_fronts = {}

    def __init__(self, note: Note, display_original_question: bool):
        super().__init__(note=note, display_original_question=display_original_question)
        self._rephrased_front = self._rephrased_fronts.get(note.id)

    @property
    def rephrased(self) -> bool:
        return self._rephrased_front is not None

    @staticmethod
    def get_model_name() -> str:
        return "basic"

    def _do_rephrase_note(self, ml_provider: MLProvider):
        self._augment_front(ml_provider=ml_provider)
        self._augment_back(ml_provider=ml_provider)

    def _do_restore_note(self):
        pass

    def _augment_front(self, ml_provider: MLProvider):
        if self._rephrased_front is None:
            self._rephrased_front = self._generate_rephrased_front(ml_provider=ml_provider)
            self._rephrased_fronts[self.id] = self._rephrased_front

    def _generate_rephrased_front(self, ml_provider: MLProvider) -> str:
        front = self._extract_note_front()
        prompt = LLM_NORMAL_NOTE_REPHRASING_FRONT_PROMPT.format(note_text=front)
        rephrased_front = ml_provider.completion(prompt=prompt)
        rephrased_front = rephrased_front.strip('"').strip("'")
        if len(rephrased_front) == 0:
            rephrased_front = f"{front}<br><br><b>[{TUTOR_NAME}]</b> Failed to rephrase note front due to ambiguity."
        return rephrased_front

    def _augment_back(self, ml_provider: MLProvider):
        pass

    def _get_rephrased_question_from_original_question(self, question: str) -> str:
        return self._rephrased_front

    def _get_original_question_from_original_note_text(self, text: str) -> str:
        return self._extract_note_front()

    def _get_original_question_from_augmented_note_text(self, text: str) -> str:
        return self._extract_note_front()

    def _extract_note_front(self) -> str:
        note = self.get_note()
        front = note["Front"]
        return front


class BasicAndReverseNoteWrapper(BasicNoteWrapper):
    _rephrased_backs = {}

    def __init__(self, note: Note, display_original_question: bool):
        super().__init__(note=note, display_original_question=display_original_question)
        self._rephrased_back = self._rephrased_backs.get(note.id)

    @property
    def rephrased(self) -> bool:
        return super().rephrased and self._rephrased_back is not None

    @staticmethod
    def get_model_name() -> str:
        return "basic (and reversed card)"

    def _do_rephrase_note(self, ml_provider: MLProvider):
        self._augment_front(ml_provider=ml_provider)
        self._augment_back(ml_provider=ml_provider)

    def _do_restore_note(self):
        pass

    def _augment_back(self, ml_provider: MLProvider):
        if self._rephrased_back is None:
            self._rephrased_back = self._generate_rephrased_back(
                ml_provider=ml_provider
            )
            self._rephrased_backs[self.id] = self._rephrased_back

    def _get_rephrased_question_from_original_question(self, question: str) -> str:
        front_string = self._extract_note_front_string()
        if question == front_string:
            rephrased_question = self._rephrased_front
        else:
            rephrased_question = self._rephrased_back
        return rephrased_question

    def _extract_note_front_string(self) -> str:
        front = self._extract_note_front()
        soup = BeautifulSoup(markup=front, features=NOTE_TEXT_PARSER)
        span = soup.find("span")
        if span is not None:
            front_string = span.string
        else:
            front_string = front
        return front_string

    def _get_original_question_from_original_note_text(self, text: str) -> str:
        question_string = self._find_first_match_in_string(
            target=text, first_sub=self._extract_note_front(), second_sub=self._extract_note_back()
        )
        return question_string

    def _get_original_question_from_augmented_note_text(self, text: str) -> str:
        rephrased_question = self._find_first_match_in_string(
            target=text, first_sub=self._rephrased_front, second_sub=self._rephrased_back
        )
        if rephrased_question == self._rephrased_front:
            original_question = self._extract_note_front()
        else:
            original_question = self._extract_note_back()
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
        back = self._extract_note_back()
        prompt = LLM_NORMAL_NOTE_REPHRASING_BACK_PROMPT.format(note_text=back)
        rephrased_back = ml_provider.completion(prompt=prompt)
        rephrased_back = rephrased_back.strip('"').strip("'")
        if len(rephrased_back) == 0:
            rephrased_back = f"{back}<br><br><b>[{TUTOR_NAME}]</b> Failed to rephrase note back due to ambiguity."
        return rephrased_back

    def _extract_note_back(self) -> str:
        note = self.get_note()
        back = note["Back"]
        return back


class ClozeNoteWrapper(NoteWrapperBase):
    _original_clozes = PersistentDict[int, str](file_name=CLOZE_DATA_FILE_NAME)
    _rephrased_clozes = {}

    def __init__(self, note: Note, display_original_question: bool):
        super().__init__(note=note, display_original_question=display_original_question)
        self._original_cloze = self._original_clozes.get(self.id)
        self._rephrased_cloze = self._rephrased_clozes.get(self.id)

    @property
    def rephrased(self) -> bool:
        is_rephrased = True
        if not self._check_editor_is_open() and self._rephrased_cloze is None:
            cloze = self._extract_cloze()
            is_rephrased = cloze == self._rephrased_cloze
        return is_rephrased

    @staticmethod
    def get_model_name() -> str:
        return "cloze"

    def rephrase_text(self, text: str, kind: str) -> str:
        augmented_text = text
        if kind == "reviewAnswer" and self._display_original_question and not self._check_editor_is_open():
            augmented_text = self._augment_note_text_answer(text=text)
        return augmented_text

    def _do_rephrase_note(self, ml_provider: MLProvider):
        if not self._check_editor_is_open():
            if self.id not in self._original_clozes:
                cloze = self._extract_cloze()
                self._original_clozes[self.id] = cloze
                self._original_clozes.save()
            if self._rephrased_cloze is None:
                self._rephrased_cloze = self._generate_rephrased_cloze(ml_provider=ml_provider)
                self._rephrased_clozes[self.id] = self._rephrased_cloze
            print(f"rephrasing cloze: {self._rephrased_cloze}")
            self._set_cloze(cloze=self._rephrased_cloze)

    def _do_restore_note(self):
        cloze = self._original_clozes.get(self.id)
        if cloze is not None:
            print(f"restoring cloze: {cloze}")
            self._set_cloze(cloze=cloze)
            del self._original_clozes[self.id]
            self._original_clozes.save()

    @staticmethod
    def _check_editor_is_open() -> bool:
        is_open = False
        target_dialogs = ["Browse (", "Edit Current"]
        for widget in mw.app.topLevelWidgets():
            if widget.objectName() == "Dialog" and widget.isVisible() and widget.windowTitle() in target_dialogs:
                is_open = True
                break
        return is_open

    def _generate_rephrased_cloze(self, ml_provider: MLProvider) -> str:
        cloze = self._extract_cloze()
        prompt = LLM_CLOZE_NOTE_REPHRASING_PROMPT.format(note_text=cloze)
        rephrased_cloze = ml_provider.completion(prompt=prompt)
        rephrased_cloze = rephrased_cloze.strip('"').strip("'")
        if len(rephrased_cloze) == 0:
            rephrased_cloze = f"{cloze}<br><br><b>[{TUTOR_NAME}]</b> Failed to rephrase cloze due to ambiguity."
        return rephrased_cloze

    def _set_cloze(self, cloze: str):
        note = self.get_note()
        note["Text"] = cloze
        mw.col.update_note(note=note)

    def _extract_cloze(self) -> str:
        cloze_text = self._extract_cloze_text()
        soup = BeautifulSoup(markup=cloze_text, features=NOTE_TEXT_PARSER)
        cloze_span = soup.find("span")
        if cloze_span is not None:
            cloze = cloze_span.string
        else:
            cloze = cloze_text
        return cloze

    def _extract_cloze_text(self) -> str:
        note = self.get_note()
        cloze_text = note["Text"]
        return cloze_text

    def _augment_note_text_answer(self, text: str) -> str:
        soup = BeautifulSoup(markup=text, features=NOTE_TEXT_PARSER)

        # Create a new <hr> tag
        hr_tag = soup.new_tag("hr")
        hr_tag['id'] = "original-cloze"
        soup.body.append(hr_tag)

        bold_tag = soup.new_tag("b")
        bold_tag.string = f"[{TUTOR_NAME}] Original Cloze"
        p_tag = soup.new_tag("p")
        p_tag.append(bold_tag)
        soup.body.append(p_tag)

        original_cloze = self._original_clozes.get(self.id)
        original_cloze_without_markers = self._remove_cloze_markers(cloze=original_cloze)
        original_cloze_soup = BeautifulSoup(markup=original_cloze_without_markers, features=NOTE_TEXT_PARSER)
        original_cloze_span = original_cloze_soup.find("span")

        if original_cloze_span is None:
            original_cloze_span = soup.new_tag("span")
            original_cloze_span.string = original_cloze_without_markers

        soup.body.append(original_cloze_span)

        modified_html = str(soup)
        return modified_html

    @staticmethod
    def _remove_cloze_markers(cloze: str) -> str:
        cloze_without_markers = re.sub(r"{{c\d::(.*?)}}", r"\1", cloze)
        return cloze_without_markers
