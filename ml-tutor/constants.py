
TUTOR_NAME = "ML-Tutor"
CARD_TEXT_PARSER = "lxml"
LLM_NORMAL_CARD_REPHRASING_FRONT_PROMPT = """
Given the Anki card front text: '{card_text}', please attempt to rephrase the card front
in a way that retains the core information and intent but alters the structure
and wording. This rephrasing should encourage understanding and recall of the concept
rather than memorization of the card's wording style. If the text is too ambiguous to 
rephrase without altering its intended meaning, return an empty string without any
further explanation why the text is ambiguous.
"""
LLM_NORMAL_CARD_REPHRASING_BACK_PROMPT = """
Given the Anki card back text: '{card_text}', please attempt to rephrase the card back
in a way that retains the core information and intent but alters the structure
and wording. This rephrasing should encourage understanding and recall of the concept
rather than memorization of the card's wording style. If the text is too ambiguous to 
rephrase without altering its intended meaning, return an empty string without any
further explanation why the text is ambiguous.
"""