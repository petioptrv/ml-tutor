from dataclasses import dataclass


@dataclass
class Prompts:
    front: str
    back: str
    cloze: str
