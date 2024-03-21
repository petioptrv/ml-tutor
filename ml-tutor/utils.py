# -*- coding: utf-8 -*-

# ML-Tutor Add-on for Anki
#
# Copyright (C) 2024 Petrov P.
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

import re

from bs4 import BeautifulSoup, Tag

from .constants import NOTE_TEXT_PARSER


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


def remove_tags(html):
    # https://www.geeksforgeeks.org/remove-all-style-scripts-and-html-tags-using-beautifulsoup/
    html = re.sub(pattern=r"<br\s*\/?>", repl="\n", string=html)  # replace breakpoints
    soup = BeautifulSoup(markup=html, features=NOTE_TEXT_PARSER)

    for data in soup(["style", "script"]):
        data.decompose()

    stripped_string = " ".join(soup.stripped_strings)
    stripped_string = strip_spaces_before_punctuation(text=stripped_string)
    return stripped_string


def build_html_paragraph_from_text(soup: BeautifulSoup, text: str) -> Tag:
    paragraph = soup.new_tag(name="p")
    lines = text.splitlines()
    paragraph.append(soup.new_string(lines[0]))
    for line in lines[1:]:
        paragraph.append(soup.new_tag(name="br"))
        paragraph.append(soup.new_string(line))
    return paragraph


def strip_spaces_before_punctuation(text: str) -> str:
    text = re.sub(r'\s([?.!"](?:\s|$))', r'\1', text)  # https://stackoverflow.com/a/18878970
    return text
