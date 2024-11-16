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

TUTOR_NAME = "ML-Tutor"
REPHRASE_CARDS_AHEAD = 3
NOTE_TEXT_PARSER = "html.parser"
DISPLAY_ORIGINAL_QUESTION_CONFIG_KEY = "display-original-question"
EASE_TARGET_CONFIG_KEY = "ease-target"
MIN_INTERVAL_DAYS_CONFIG_KEY = "min-interval-days"
MIN_REVIEWS_CONFIG_KEY = "min-reviews"
LLM_BASIC_NOTE_REPHRASING_FRONT_PROMPT_CONFIG_KEY = "basic-note-front-prompt"
LLM_BASIC_NOTE_REPHRASING_FRONT_PROMPT = """
Given the spaced-repetition note front text: '{note_front}', please attempt to rephrase
the note front in a way that retains the core information and intent but alters the
structure and wording. This rephrasing should encourage understanding and recall of the
concept rather than memorization of the exact structure of the question. If the text is
too ambiguous to rephrase without altering its intended meaning, return an empty string
without any further explanation why the text is ambiguous.
"""
LLM_BASIC_AND_REVERSE_NOTE_REPHRASING_BACK_PROMPT_CONFIG_KEY = "basic-and-reverse-note-back-prompt"
LLM_NORMAL_NOTE_REPHRASING_BACK_PROMPT = """
Given the spaced-repetition note back text: '{note_back}', please attempt to rephrase
the note back in a way that retains the core information and intent but alters the
structure and wording. This rephrasing should encourage understanding and recall of the
concept rather than memorization of the exact structure of the question. If the text is
too ambiguous to rephrase without altering its intended meaning, return an empty string
without any further explanation why the text is ambiguous.
"""
LLM_CLOZE_NOTE_REPHRASING_PROMPT_CONFIG_KEY = "cloze-note-prompt"
LLM_CLOZE_NOTE_REPHRASING_PROMPT = """
Given the spaced-repetition cloze-deletion note '{note_cloze}', please reword it in a
way that retains the core information and intent but alters the structure and wording.
The goal is to enhance understanding and recall without relying on the exact structure
of the question. Keep the same number of fill-in-the-blank spaces. If the text is too
ambiguous to rephrase without altering its intended meaning, return an empty string
without any further explanation why the text is ambiguous.
"""

ADD_ON_ID = "1505658371"
