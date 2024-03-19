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
