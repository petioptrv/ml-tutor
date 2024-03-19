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

import json

from aqt import gui_hooks, mw
from aqt.utils import showCritical

from .notes_wrappers import NotesWrapperFactory
from .constants import TUTOR_NAME
from .ml_tutor import MLTutor
from .ml.ml_provider import MLProvider
from .ml.open_ai import OpenAI


class AnkiAddon:
    """Anki add-on composition root."""
    # todo: extract the ml-provider creation in a factory method?

    def __init__(self):
        notes_decorator_factory = NotesWrapperFactory()
        config = mw.addonManager.getConfig(__name__)
        ml_provider = self._initialize_ml_provider(config=config)
        self._ml_tutor = MLTutor(
            notes_decorator_factory=notes_decorator_factory,
            ml_provider=ml_provider,
            display_original_question=config["display-original-question"],
        )
        self._add_hooks()

    def _add_hooks(self):
        gui_hooks.addon_config_editor_will_update_json.append(self._on_config_update)
        gui_hooks.collection_did_load.append(self._ml_tutor.on_collection_load)
        gui_hooks.card_will_show.append(self._ml_tutor.on_card_will_show)
        gui_hooks.reviewer_did_show_answer.append(self._ml_tutor.on_reviewer_did_show_answer)

    def _on_config_update(self, text: str, _: str) -> str:
        config = json.loads(text)
        self._set_ml_provider(config=config)
        self._ml_tutor.set_display_original_question(display_original_question=config["display-original-question"])
        return text

    def _set_ml_provider(self, config: dict):
        ml_provider = self._initialize_ml_provider(config=config)
        self._ml_tutor.set_ml_provider(ml_provider=ml_provider)

    @staticmethod
    def _initialize_ml_provider(config: dict) -> MLProvider:
        openai_api_key = config["openai-key"]
        openai_generative_model = config["openai-generative-model"]
        openai = OpenAI(api_key=openai_api_key, generative_model=openai_generative_model)

        if openai.check_api_key() is False:
            showCritical(f"[{TUTOR_NAME}] OpenAI API key is invalid.")
        elif openai.check_model() is False:
            valid_models = openai.get_valid_models()
            showCritical(
                f"[{TUTOR_NAME}] OpenAI model is invalid."
                f"<br><br><b>Valid Models</b><br>{'<br>'.join([m.id for m in valid_models])}"
            )

        return openai
