
TUTOR_NAME = "ML-Tutor"
REPHRASE_CARDS_AHEAD = 3
NOTE_TEXT_PARSER = "html.parser"
LLM_NORMAL_NOTE_REPHRASING_FRONT_PROMPT = """
Given the spaced-repetition note front text: '{note_text}', please attempt to rephrase
the note front in a way that retains the core information and intent but alters the
structure and wording. This rephrasing should encourage understanding and recall of the
concept rather than memorization of the exact structure of the question. If the text is
too ambiguous to rephrase without altering its intended meaning, return an empty string
without any further explanation why the text is ambiguous.
"""
LLM_NORMAL_NOTE_REPHRASING_BACK_PROMPT = """
Given the spaced-repetition note back text: '{note_text}', please attempt to rephrase
the note back in a way that retains the core information and intent but alters the
structure and wording. This rephrasing should encourage understanding and recall of the
concept rather than memorization of the exact structure of the question. If the text is
too ambiguous to rephrase without altering its intended meaning, return an empty string
without any further explanation why the text is ambiguous.
"""
LLM_CLOZE_NOTE_REPHRASING_PROMPT = """
Given the spaced-repetition cloze-deletion note '{note_text}', please reword it in a
way that retains the core information and intent but alters the structure and wording.
The goal is to enhance understanding and recall without relying on the exact structure
of the question. Keep the same number of fill-in-the-blank spaces. If the text is too
ambiguous to rephrase without altering its intended meaning, return an empty string
without any further explanation why the text is ambiguous.
"""