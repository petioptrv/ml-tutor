from abc import ABC, abstractmethod


class MLProvider(ABC):
    @abstractmethod
    def completion(self, prompt: str) -> str:
        raise NotImplementedError()
