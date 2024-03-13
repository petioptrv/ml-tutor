from typing import Optional


class NotesCache:
    def __init__(self):
        self._cache = {}

    def store_note(self, note_id, note_content):
        self._cache[note_id] = note_content

    def get_cached_note(self, note_id) -> Optional[str]:
        return self._cache.get(note_id, None)
