from typing import List

from anki.cards_pb2 import Card
from anki.collection import Collection
from anki.notes_pb2 import Note
from anki.scheduler.v3 import QueuedCards
from aqt import mw
from aqt.editor import Editor

from .constants import REPHRASED_NOTES_FILE_NAME
from .persistent_structures import PersistentSet
from .notes_wrappers import NotesWrapperFactory, NoteWrapperBase
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
        self._rephrased_notes = PersistentSet[int](file_name=REPHRASED_NOTES_FILE_NAME)

    def set_ml_provider(self, ml_provider: MLProvider):
        self._ml_provider = ml_provider

    def set_display_original_question(self, display_original_question: bool):
        self._display_original_question = display_original_question

    def on_collection_load(self, _: Collection):
        print("MLTutor.on_collection_load")
        self._restore_all_notes()
        self._start_next_cards_in_queue()

    def on_card_will_show(self, text: str, card: Card, kind: str) -> str:
        print("MLTutor.on_card_will_show")
        self._start_next_cards_in_queue()
        note = self._get_note_from_card(card=card)
        decorated_note = self._notes_decorator_factory.get_wrapped_note(
            note=note, display_original_question=self._display_original_question
        )
        decorated_note.rephrase_note(ml_provider=self._ml_provider)
        decorated_note.wait_rephrasing()
        self._add_note_to_rephrased_notes(note=note)
        text = decorated_note.rephrase_text(text=text, kind=kind)
        return text

    def on_reviewer_did_show_answer(self, card: Card):
        print("MLTutor.on_reviewer_did_show_answer")
        note = self._get_note_from_card(card=card)
        decorated_note = self._notes_decorator_factory.get_wrapped_note(note=note)
        decorated_note.restore_note()
        self._remove_note_from_rephrased_notes(note=note)
        self._start_next_cards_in_queue()

    def on_profile_will_close(self):
        print("MLTutor.on_profile_will_close")
        self._restore_all_notes()

    def on_editor_did_init(self, _: Editor):
        print("MLTutor.on_editor_did_init")
        self._restore_all_notes()

    def on_sync_will_start(self):
        print("MLTutor.on_sync_will_start")
        self._restore_all_notes()

    def on_sync_did_finish(self):
        print("MLTutor.on_sync_did_finish")
        self._start_next_cards_in_queue()

    def _get_all_decorated_notes(self) -> List[NoteWrapperBase]:
        decorated_notes = [
            self._notes_decorator_factory.get_wrapped_note(
                note=mw.col.get_note(id=rephrased_note_id),
                display_original_question=self._display_original_question,
            )
            for rephrased_note_id in self._rephrased_notes
        ]
        return decorated_notes

    def _start_next_cards_in_queue(self):
        col = mw.col
        next_cards_queue: QueuedCards = col.sched.get_queued_cards(fetch_limit=2)

        for card in next_cards_queue.cards:
            note = self._get_note_from_card(card=card.card)
            decorated_note = self._notes_decorator_factory.get_wrapped_note(
                note=note, display_original_question=self._display_original_question
            )
            decorated_note.rephrase_note(ml_provider=self._ml_provider)
            self._rephrased_notes.add(decorated_note.id)

        self._rephrased_notes.save()

    def _restore_all_notes(self):
        decorated_notes = self._get_all_decorated_notes()
        for decorated_note in decorated_notes:
            decorated_note.restore_note()
        for decorated_note in decorated_notes:
            decorated_note.wait_restoration()
            self._rephrased_notes.remove(decorated_note.id)
        self._rephrased_notes.save()

    def _add_note_to_rephrased_notes(self, note: Note):
        if note.id not in self._rephrased_notes:
            self._rephrased_notes.add(note.id)
            self._rephrased_notes.save()

    def _remove_note_from_rephrased_notes(self, note: Note):
        if note.id in self._rephrased_notes:
            self._rephrased_notes.remove(note.id)
            self._rephrased_notes.save()

    @staticmethod
    def _get_note_from_card(card: Card) -> Note:
        note = mw.col.get_card(card.id).note()
        return note
