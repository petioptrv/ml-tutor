# -*- coding: utf-8 -*-

# ML-Tutor Add-on for Anki
#
# Copyright (C)  2016-2019 Petrov P.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version, with the additions
# listed at the end of the license file that accompanied this program
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# NOTE: This program is subject to certain additional terms pursuant to
# Section 7 of the GNU Affero General Public License.  You should have
# received a copy of these additional terms immediately following the
# terms and conditions of the GNU Affero General Public License that
# accompanied this program.
#
# If not, please request a copy through one of the means of contact
# listed here: <mailto:petioptrv@icloud.com>.
#
# Any modifications to this file must keep this entire header intact.

import inspect
import re
from abc import ABC, abstractmethod, ABCMeta
from collections import defaultdict
from copy import copy
from threading import Event
from typing import Union, Optional, Dict, List, Tuple

from anki.notes_pb2 import Note
from aqt import mw
from bs4 import BeautifulSoup, Tag

from .utils import Singleton, remove_tags, strip_spaces_before_punctuation, build_html_paragraph_from_text
from .constants import (
    LLM_NORMAL_NOTE_REPHRASING_FRONT_PROMPT,
    TUTOR_NAME,
    NOTE_TEXT_PARSER,
    LLM_NORMAL_NOTE_REPHRASING_BACK_PROMPT,
    LLM_CLOZE_NOTE_REPHRASING_PROMPT,
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


class NoteWrapperBase(ABC, metaclass=DecoratorRegistryMeta):
    @property
    @abstractmethod
    def rephrased(self) -> bool:
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

    def __init__(self, note: Note, display_original_question: bool):
        self._note_id = note.id
        self._display_original_question = display_original_question
        self._is_rephrasing: Optional[Event] = None

    @property
    def id(self) -> Union[int, None]:
        return self.get_note().id

    def get_note(self) -> Note:
        return mw.col.get_note(id=self._note_id)

    def set_display_original_question(self, display_original_question: bool):
        self._display_original_question = display_original_question

    def rephrase_note(self, ml_provider: MLProvider) -> int:
        self.wait_rephrasing()
        self._is_rephrasing = Event()
        self._do_rephrase_note(ml_provider=ml_provider)
        is_augmenting = self._is_rephrasing
        self._is_rephrasing = None
        is_augmenting.set()
        return 0

    def wait_rephrasing(self):
        self._is_rephrasing and self._is_rephrasing.wait()


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


class BasicNoteWrapperBase(NoteWrapperBase, ABC):
    @abstractmethod
    def _get_rephrased_question_from_original_question(self, question: str) -> str:
        ...

    @abstractmethod
    def _get_original_question_from_original_note_text(self, text: str) -> str:
        ...

    @abstractmethod
    def _get_original_question_from_rephrased_note_text(self, text: str) -> str:
        ...

    def rephrase_text(self, text: str, kind: str) -> str:
        rephrased_text, original_question_soup = self._rephrase_note_text_question(text=text)
        if kind == "reviewAnswer" and self._display_original_question:
            rephrased_text = self._append_note_text_answer(
                original_text=text, rephrased_question_text=rephrased_text
            )
            if self._display_original_question:
                rephrased_text = self._append_original_question(
                    rephrased_text=rephrased_text, original_question_soup=original_question_soup
                )
        return rephrased_text

    def _rephrase_note_text_question(self, text: str) -> Tuple[str, BeautifulSoup]:
        soup = BeautifulSoup(markup=text, features=NOTE_TEXT_PARSER)
        rephrased_question_soup = BeautifulSoup(features=NOTE_TEXT_PARSER)
        rephrased_question_soup.append(copy(soup.find(name="style")))
        original_question, original_question_soup = self._get_question_from_original_text(text=text)
        rephrased_question = self._get_rephrased_question_from_original_question(
            question=original_question
        )
        rephrased_question_paragraph = build_html_paragraph_from_text(
            soup=rephrased_question_soup, text=rephrased_question
        )
        rephrased_question_soup.append(rephrased_question_paragraph)
        return str(rephrased_question_soup), original_question_soup

    def _get_question_from_original_text(self, text: str) -> Tuple[str, BeautifulSoup]:
        soup = BeautifulSoup(markup=text, features=NOTE_TEXT_PARSER)
        question_soup = BeautifulSoup(features=NOTE_TEXT_PARSER)
        page_elements = list(soup.find("style").next_siblings)
        for element in page_elements:
            if isinstance(element, Tag) and element.name == "hr":
                break
            else:
                question_soup.append(copy(element))
        if len(question_soup) != 0:
            question = remove_tags(html=str(question_soup))
        else:
            question = self._get_original_question_from_original_note_text(text=text)
            question_soup = BeautifulSoup(markup=question, features=NOTE_TEXT_PARSER)
        return question, question_soup

    def _append_note_text_answer(self, original_text: str, rephrased_question_text: str) -> str:
        rephrased_soup = BeautifulSoup(markup=rephrased_question_text, features=NOTE_TEXT_PARSER)

        original_answer_tags = self._get_answer_page_elements_from_original_text(text=original_text)
        for tag in original_answer_tags:
            rephrased_soup.append(tag)

        return str(rephrased_soup)

    @staticmethod
    def _append_original_question(rephrased_text: str, original_question_soup: BeautifulSoup) -> str:
        rephrased_soup = BeautifulSoup(markup=rephrased_text, features=NOTE_TEXT_PARSER)

        # Create a new <hr> tag
        hr_tag = rephrased_soup.new_tag(name="hr")
        hr_tag["id"] = "original-question"
        rephrased_soup.append(hr_tag)

        bold_tag = rephrased_soup.new_tag(name="b")
        bold_tag.string = f"[{TUTOR_NAME}] Original Question"
        p_tag = rephrased_soup.new_tag(name="p")
        p_tag.append(bold_tag)
        rephrased_soup.append(p_tag)

        for page_element in original_question_soup.contents:
            rephrased_soup.append(copy(page_element))

        rephrased_text = str(rephrased_soup)
        return rephrased_text

    @staticmethod
    def _get_answer_page_elements_from_original_text(text: str) -> List[Tag]:
        soup = BeautifulSoup(markup=text, features=NOTE_TEXT_PARSER)
        answer_page_elements = []
        page_elements = list(soup.find("style").next_siblings)
        next_answer_tag: Optional[Tag] = None
        while len(page_elements) != 0 and len(answer_page_elements) == 0:
            element = page_elements.pop(0)
            if isinstance(element, Tag) and element.name == "hr" and element.get("id") == "answer":
                answer_page_elements.append(copy(element))
                next_answer_tag = element.next_sibling
        while next_answer_tag is not None and next_answer_tag.name != "hr":
            answer_page_elements.append(copy(next_answer_tag))
            next_answer_tag = next_answer_tag.next_sibling
        if len(answer_page_elements) == 0:
            hr_tag = soup.new_tag("hr")
            hr_tag["id"] = "answer"
            answer_page_elements.append(hr_tag)
            answer_paragraph = soup.new_tag("p")
            answer = f"[{TUTOR_NAME}] Failed to extract original answer."
            answer_paragraph.string = answer
            answer_page_elements.append(answer_paragraph)
        return answer_page_elements


class BasicNoteWrapper(BasicNoteWrapperBase):
    _original_front_texts = {}
    _rephrased_fronts = {}

    @property
    def rephrased(self) -> bool:
        return self._check_front_is_rephrased()

    @staticmethod
    def get_model_name() -> str:
        return "basic"

    def _do_rephrase_note(self, ml_provider: MLProvider):
        self._augment_front(ml_provider=ml_provider)
        self._augment_back(ml_provider=ml_provider)

    def _augment_front(self, ml_provider: MLProvider):
        if not self._check_front_is_rephrased():
            self._rephrased_fronts[self.id] = self._generate_rephrased_front(ml_provider=ml_provider)
            self._original_front_texts[self.id] = self._extract_front_text()

    def _check_front_is_rephrased(self) -> bool:
        rephrased = False
        rephrased_front = self._rephrased_fronts.get(self.id)
        if rephrased_front is not None:
            current_front = self._extract_front_text()
            original_front = self._original_front_texts.get(self.id)
            if current_front == original_front:
                rephrased = True
        return rephrased

    def _generate_rephrased_front(self, ml_provider: MLProvider) -> str:
        front = self._extract_front()
        prompt = LLM_NORMAL_NOTE_REPHRASING_FRONT_PROMPT.format(note_text=front)
        rephrased_front = ml_provider.completion(prompt=prompt)
        rephrased_front = rephrased_front.strip('"').strip("'")
        if len(rephrased_front) == 0:
            rephrased_front = f"{front}<br><br><b>[{TUTOR_NAME}]</b> Failed to rephrase note front due to ambiguity."
        return rephrased_front

    def _augment_back(self, ml_provider: MLProvider):
        pass

    def _get_rephrased_question_from_original_question(self, question: str) -> str:
        return self._rephrased_fronts[self.id]

    def _get_original_question_from_original_note_text(self, text: str) -> str:
        return self._extract_front_text()

    def _get_original_question_from_rephrased_note_text(self, text: str) -> str:
        return self._extract_front_text()

    def _extract_front(self) -> str:
        front_text = self._extract_front_text()
        front = remove_tags(html=front_text)
        return front

    def _extract_front_text(self) -> str:
        note = self.get_note()
        front = note["Front"]
        return front


class BasicAndReverseNoteWrapper(BasicNoteWrapper):
    _original_back_texts = {}
    _rephrased_backs = {}

    @property
    def rephrased(self) -> bool:
        return super().rephrased and self._check_back_is_rephrased()

    @staticmethod
    def get_model_name() -> str:
        return "basic (and reversed card)"

    def _do_rephrase_note(self, ml_provider: MLProvider):
        self._augment_front(ml_provider=ml_provider)
        self._augment_back(ml_provider=ml_provider)

    def _augment_back(self, ml_provider: MLProvider):
        if not self._check_back_is_rephrased():
            self._rephrased_backs[self.id] = self._generate_rephrased_back(ml_provider=ml_provider)
            self._original_back_texts[self.id] = self._extract_back_text()

    def _check_back_is_rephrased(self) -> bool:
        rephrased = False
        rephrased_back = self._rephrased_backs.get(self.id)
        if rephrased_back is not None:
            current_back = self._extract_back_text()
            original_back = self._original_back_texts.get(self.id)
            if current_back == original_back:
                rephrased = True
        return rephrased

    def _get_rephrased_question_from_original_question(self, question: str) -> str:
        front = self._extract_front()
        if question == front:
            rephrased_question = self._rephrased_fronts[self.id]
        else:
            rephrased_question = self._rephrased_backs[self.id]
        return rephrased_question

    def _get_original_question_from_original_note_text(self, text: str) -> str:
        question_string = self._find_first_match_in_string(
            target=text, first_sub=self._extract_front_text(), second_sub=self._extract_back_text()
        )
        return question_string

    def _get_original_question_from_rephrased_note_text(self, text: str) -> str:
        rephrased_front = self._rephrased_fronts[self.id]
        rephrased_back = self._rephrased_backs[self.id]
        rephrased_question = self._find_first_match_in_string(
            target=text, first_sub=rephrased_front, second_sub=rephrased_back
        )
        if rephrased_question == rephrased_front:
            original_question = self._extract_front_text()
        else:
            original_question = self._extract_back_text()
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
        back = self._extract_back()
        prompt = LLM_NORMAL_NOTE_REPHRASING_BACK_PROMPT.format(note_text=back)
        rephrased_back = ml_provider.completion(prompt=prompt)
        rephrased_back = rephrased_back.strip('"').strip("'")
        if len(rephrased_back) == 0:
            rephrased_back = f"{back}<br><br><b>[{TUTOR_NAME}]</b> Failed to rephrase note back due to ambiguity."
        return rephrased_back

    def _extract_back(self) -> str:
        back_text = self._extract_back_text()
        back = remove_tags(html=back_text)
        return back

    def _extract_back_text(self) -> str:
        note = self.get_note()
        back = note["Back"]
        return back


class ClozeNoteWrapper(NoteWrapperBase):
    _original_clozes = {}
    _original_clozes_pieces: Dict[int, Dict[int, List[str]]] = {}
    _rephrased_clozes = {}

    def __init__(self, note: Note, display_original_question: bool):
        super().__init__(note=note, display_original_question=display_original_question)
        self._original_cloze = self._original_clozes.get(note.id)
        self._rephrased_cloze = self._rephrased_clozes.get(self.id)

    @property
    def rephrased(self) -> bool:
        is_rephrased = self._rephrased_cloze is not None  # todo: check if the card has been modified
        return is_rephrased

    @staticmethod
    def get_model_name() -> str:
        return "cloze"

    def rephrase_text(self, text: str, kind: str) -> str:
        if kind == "reviewQuestion":
            augmented_text = self._rephrase_note_text_cloze(text=text, hide=True)
        else:
            assert kind == "reviewAnswer"  # need to handle all possibilities
            augmented_text = self._rephrase_note_text_cloze(text=text, hide=False)
            if self._display_original_question:
                augmented_text = self._append_original_question(
                    text=text, augmented_text=augmented_text
                )
        return augmented_text

    def _do_rephrase_note(self, ml_provider: MLProvider):
        if self._rephrased_cloze is None:
            original_cloze = self._extract_cloze()
            self._original_cloze = strip_spaces_before_punctuation(text=original_cloze)
            self._rephrased_cloze = self._generate_rephrased_cloze(ml_provider=ml_provider)
            self._rephrased_clozes[self.id] = self._rephrased_cloze

    def _generate_rephrased_cloze(self, ml_provider: MLProvider) -> str:
        cloze = self._extract_cloze()
        prompt = LLM_CLOZE_NOTE_REPHRASING_PROMPT.format(note_text=cloze)
        rephrased_cloze = ml_provider.completion(prompt=prompt)
        rephrased_cloze = rephrased_cloze.strip('"').strip("'")
        if len(rephrased_cloze) == 0:
            rephrased_cloze = f"{cloze}<br><br><b>[{TUTOR_NAME}]</b> Failed to rephrase cloze due to ambiguity."
        return rephrased_cloze

    def _rephrase_note_text_cloze(self, text: str, hide: bool) -> str:
        target_cloze_number = self._get_target_cloze_number(text=text)
        if target_cloze_number is None:
            rephrased_text = f"{text}<br><br><b>[{TUTOR_NAME}]</b> Failed to determine which cloze was deleted."
        else:
            rephrased_text = self._get_text_paragraph_for_cloze_number(
                target_cloze_number=target_cloze_number,
                cloze=self._rephrased_cloze,
                hide=hide,
            )
            original_soup = BeautifulSoup(markup=text, features=NOTE_TEXT_PARSER)
            style_tag = original_soup.find("style")
            if style_tag is not None:
                rephrased_soup = BeautifulSoup(features=NOTE_TEXT_PARSER)
                rephrased_soup.append(style_tag)
                rephrased_soup.append(BeautifulSoup(markup=rephrased_text, features=NOTE_TEXT_PARSER).find("p"))
                rephrased_text = str(rephrased_soup)
        return rephrased_text

    @staticmethod
    def _get_target_cloze_number(text: str) -> Optional[int]:
        soup = BeautifulSoup(markup=text, features=NOTE_TEXT_PARSER)
        cloze_span = soup.find("span", class_="cloze")
        target_cloze_number = None
        if cloze_span is not None:
            target_cloze_number = int(cloze_span["data-ordinal"])
        return target_cloze_number

    def _append_original_question(self, text: str, augmented_text: str) -> str:
        soup = BeautifulSoup(markup=augmented_text, features=NOTE_TEXT_PARSER)

        # Create a new <hr> tag
        hr_tag = soup.new_tag("hr")
        hr_tag["id"] = "original-cloze"
        soup.append(hr_tag)

        bold_tag = soup.new_tag("b")
        bold_tag.string = f"[{TUTOR_NAME}] Original Cloze"
        p_tag = soup.new_tag("p")
        p_tag.append(bold_tag)
        soup.append(p_tag)

        original_soup = BeautifulSoup(markup=text, features=NOTE_TEXT_PARSER)
        original_cloze_paragraph_page_elements = list(original_soup.find("style").next_siblings)

        if len(original_cloze_paragraph_page_elements) != 0:
            for element in original_cloze_paragraph_page_elements:
                soup.append(copy(element))
        else:
            target_cloze_number = self._get_target_cloze_number(text=text)
            original_cloze_paragraph_page_elements = self._get_text_paragraph_for_cloze_number(
                target_cloze_number=target_cloze_number,
                cloze=self._original_cloze,
                hide=False,
            )
            original_cloze_soup = BeautifulSoup(markup=original_cloze_paragraph_page_elements, features=NOTE_TEXT_PARSER)
            soup.append(original_cloze_soup.find("p"))

        modified_html = str(soup)
        return modified_html

    def _get_text_paragraph_for_cloze_number(
        self, target_cloze_number: int, cloze: str, hide: bool
    ) -> str:
        cloze_pieces = self._extract_cloze_pieces(cloze=cloze)
        for cloze_number, cloze_number_pieces in cloze_pieces.items():
            span_class = "cloze" if cloze_number == target_cloze_number else "cloze-inactive"
            if hide and cloze_number == target_cloze_number:
                cloze = self._replace_next_cloze_deletion(
                    cloze=cloze,
                    cloze_deletion_number=cloze_number,
                    new_text=(
                        f"<span class=\"{span_class}\" data-ordinal=\"{cloze_number}\">[...]</span>"
                    ),
                )
            else:
                for cloze_number_piece in cloze_number_pieces:
                    cloze = self._replace_next_cloze_deletion(
                        cloze=cloze,
                        cloze_deletion_number=cloze_number,
                        new_text=(
                            f"<span class=\"{span_class}\" data-ordinal=\"{cloze_number}\">{cloze_number_piece}</span>"
                        ),
                        count=1,
                    )
        cloze_text = self._remove_cloze_markers(cloze=cloze)
        cloze_text = f"<p>{cloze_text}</p>"
        return cloze_text

    @staticmethod
    def _extract_cloze_pieces(cloze: str) -> Dict[int, List[str]]:
        cloze_pieces = defaultdict(list)
        for i, match in enumerate(re.finditer(r"{{c(\d)::(.*?)}}", cloze)):
            cloze_pieces[int(match.group(1))].append(match.group(2))
        return cloze_pieces

    def _extract_cloze(self) -> str:
        cloze_text = self._extract_cloze_text()
        cloze = remove_tags(html=cloze_text)
        return cloze

    def _extract_cloze_text(self) -> str:
        note = self.get_note()
        cloze_text = note["Text"]
        return cloze_text

    @staticmethod
    def _remove_cloze_markers(cloze: str) -> str:
        cloze_without_markers = re.sub(r"{{c\d::(.*?)}}", r"\1", cloze)
        return cloze_without_markers

    @staticmethod
    def _replace_next_cloze_deletion(cloze: str, cloze_deletion_number: int, new_text: str, count=0) -> str:
        pattern = r"{{c" + str(cloze_deletion_number) + r"::(.*?)}}"
        cloze_with_replacement = re.sub(pattern, new_text, cloze, count=count)
        return cloze_with_replacement
