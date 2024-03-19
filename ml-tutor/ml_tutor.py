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

from anki.cards_pb2 import Card
from anki.collection import Collection
from anki.notes_pb2 import Note
from anki.scheduler.v3 import QueuedCards
from aqt import mw
from qt.aqt.operations import QueryOp

from .constants import REPHRASE_CARDS_AHEAD, TUTOR_NAME
from .notes_wrappers import NotesWrapperFactory
from .ml.ml_provider import MLProvider


class MLTutor:
    # todo: refactor into MLTutor and AnkiMLTutor (separate the Anki-specific code)

    def __init__(
        self,
        notes_decorator_factory: NotesWrapperFactory,
        ml_provider: MLProvider,
        display_original_question: bool = True,
    ):
        self._notes_decorator_factory = notes_decorator_factory
        self._ml_provider = ml_provider
        self._display_original_question = display_original_question

    def set_ml_provider(self, ml_provider: MLProvider):
        self._ml_provider = ml_provider

    def set_display_original_question(self, display_original_question: bool):
        self._display_original_question = display_original_question

    def on_collection_load(self, _: Collection):
        self._start_next_cards_in_queue()

    def on_card_will_show(self, text: str, card: Card, kind: str) -> str:
        self._start_next_cards_in_queue()
        note = self._get_note_from_card(card=card)
        decorated_note = self._notes_decorator_factory.get_wrapped_note(
            note=note, display_original_question=self._display_original_question
        )
        if not decorated_note.rephrased:
            op = QueryOp(
                parent=mw,
                op=lambda _: decorated_note.rephrase_note(ml_provider=self._ml_provider),
                success=lambda _: _,
            )
            op.with_progress(label=f"[{TUTOR_NAME}] Rephrasing note.").run_in_background()

        text = decorated_note.rephrase_text(text=text, kind=kind)
        return text

    def on_reviewer_did_show_answer(self, _: Card):
        self._start_next_cards_in_queue()

    def _start_next_cards_in_queue(self):
        op = QueryOp(
            parent=mw,
            op=lambda _: self._do_start_next_cards_in_queue(),
            success=lambda _: _,
        )
        op.run_in_background()

    def _do_start_next_cards_in_queue(self):
        col = mw.col
        next_cards_queue: QueuedCards = col.sched.get_queued_cards(fetch_limit=REPHRASE_CARDS_AHEAD)

        for card in next_cards_queue.cards:
            note = self._get_note_from_card(card=card.card)
            decorated_note = self._notes_decorator_factory.get_wrapped_note(
                note=note, display_original_question=self._display_original_question
            )
            decorated_note.rephrase_note(ml_provider=self._ml_provider)

    @staticmethod
    def _get_note_from_card(card: Card) -> Note:
        note = mw.col.get_card(card.id).note()
        return note
