# -*- coding: utf-8 -*-

# ML-Tutor Add-on for Anki
#
# Copyright (C)  2024 Petrov P.
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
from typing import Optional

from aqt import gui_hooks, mw
from aqt.utils import showCritical, showInfo

from prompts import Prompts
from notes_wrappers import NotesWrapperFactory
from constants import TUTOR_NAME, ADD_ON_ID, DISPLAY_ORIGINAL_QUESTION_CONFIG_KEY, EASE_TARGET_CONFIG_KEY, \
    MIN_INTERVAL_DAYS_CONFIG_KEY, MIN_REVIEWS_CONFIG_KEY, LLM_BASIC_NOTE_REPHRASING_FRONT_PROMPT_CONFIG_KEY, \
    LLM_BASIC_NOTE_REPHRASING_FRONT_PROMPT, LLM_BASIC_AND_REVERSE_NOTE_REPHRASING_BACK_PROMPT_CONFIG_KEY, \
    LLM_NORMAL_NOTE_REPHRASING_BACK_PROMPT, LLM_CLOZE_NOTE_REPHRASING_PROMPT_CONFIG_KEY, \
    LLM_CLOZE_NOTE_REPHRASING_PROMPT
from ml_tutor import MLTutor
from ml.ml_provider import MLProvider
from ml.open_ai import OpenAI


class AnkiAddon:
    """Anki add-on composition root."""
    # todo: extract the ml-provider creation in a factory method?

    def __init__(self):
        self._notes_decorator_factory = NotesWrapperFactory()
        config = mw.addonManager.getConfig(TUTOR_NAME)
        self._ml_tutor: Optional[MLTutor] = None
        gui_hooks.addon_config_editor_will_update_json.append(self._on_config_update)
        self._on_config_update(json.dumps(config), __name__)

    def _on_config_update(self, text: str, add_on_id: str) -> str:
        if add_on_id in (ADD_ON_ID, TUTOR_NAME.lower(), __name__):
            config = json.loads(text)
            ml_provider = self._initialize_ml_provider(config=config)
            prompts = Prompts(
                front=config[LLM_BASIC_NOTE_REPHRASING_FRONT_PROMPT_CONFIG_KEY] or LLM_BASIC_NOTE_REPHRASING_FRONT_PROMPT,
                back=config[LLM_BASIC_AND_REVERSE_NOTE_REPHRASING_BACK_PROMPT_CONFIG_KEY] or LLM_NORMAL_NOTE_REPHRASING_BACK_PROMPT,
                cloze=config[LLM_CLOZE_NOTE_REPHRASING_PROMPT_CONFIG_KEY] or LLM_CLOZE_NOTE_REPHRASING_PROMPT,
            )
            if ml_provider is None:
                if self._ml_tutor is not None:
                    self._remove_tutor_hooks()
                self._ml_tutor = None
            elif self._ml_tutor is None:
                self._ml_tutor = MLTutor(
                    notes_decorator_factory=self._notes_decorator_factory,
                    prompts=prompts,
                    display_original_question=config[DISPLAY_ORIGINAL_QUESTION_CONFIG_KEY],
                    ml_provider=ml_provider,
                    ease_target=config[EASE_TARGET_CONFIG_KEY],
                    min_interval_days=config[MIN_INTERVAL_DAYS_CONFIG_KEY],
                    min_reviews=config[MIN_REVIEWS_CONFIG_KEY],
                )
                self._add_tutor_hooks()
            if self._ml_tutor is not None:
                self._ml_tutor.set_ml_provider(ml_provider=ml_provider)
                self._ml_tutor.set_prompts(prompts=prompts)
                self._ml_tutor.set_display_original_question(
                    display_original_question=config[DISPLAY_ORIGINAL_QUESTION_CONFIG_KEY]
                )
                self._ml_tutor.set_ease_target(ease_target=config[EASE_TARGET_CONFIG_KEY])
                self._ml_tutor.set_min_interval_days(min_interval_days=config[MIN_INTERVAL_DAYS_CONFIG_KEY])
                self._ml_tutor.set_min_reviews(min_reviews=config[MIN_REVIEWS_CONFIG_KEY])
        return text

    def _add_tutor_hooks(self):
        if self._ml_tutor.on_collection_load not in gui_hooks.collection_did_load._hooks:
            gui_hooks.collection_did_load.append(self._ml_tutor.on_collection_load)
        if self._ml_tutor.on_card_will_show not in gui_hooks.card_will_show._hooks:
            gui_hooks.card_will_show.append(self._ml_tutor.on_card_will_show)
        if self._ml_tutor.on_reviewer_did_show_answer not in gui_hooks.reviewer_did_show_answer._hooks:
            gui_hooks.reviewer_did_show_answer.append(self._ml_tutor.on_reviewer_did_show_answer)

    def _remove_tutor_hooks(self):
        if self._ml_tutor.on_collection_load in gui_hooks.collection_did_load._hooks:
            gui_hooks.collection_did_load.remove(self._ml_tutor.on_collection_load)
        if self._ml_tutor.on_card_will_show in gui_hooks.card_will_show._hooks:
            gui_hooks.card_will_show.remove(self._ml_tutor.on_card_will_show)
        if self._ml_tutor.on_reviewer_did_show_answer in gui_hooks.reviewer_did_show_answer._hooks:
            gui_hooks.reviewer_did_show_answer.remove(self._ml_tutor.on_reviewer_did_show_answer)

    @staticmethod
    def _initialize_ml_provider(config: dict) -> Optional[MLProvider]:
        openai_api_key = config["openai-key"]
        openai = None
        if openai_api_key == "":
            showInfo(f"[{TUTOR_NAME}] OpenAI API key is not set. Please set it via the add-on settings.")
        else:
            openai_generative_model = config["openai-generative-model"]
            openai = OpenAI(api_key=openai_api_key, generative_model=openai_generative_model)

            if openai.check_connected_to_web() is False:
                showCritical(f"[{TUTOR_NAME}] OpenAI API server is not reachable.", help=None)
                openai = None
            elif openai.check_api_key() is False:
                showCritical(f"[{TUTOR_NAME}] OpenAI API key is invalid.", help=None)
                openai = None
            elif openai.check_model() is False:
                valid_models = openai.get_valid_models()
                showCritical(
                    f"[{TUTOR_NAME}] OpenAI model is invalid."
                    f"<br><br><b>Valid Models</b><br>{'<br>'.join([m for m in valid_models])}",
                    help=None,
                )
                openai = None

        return openai
