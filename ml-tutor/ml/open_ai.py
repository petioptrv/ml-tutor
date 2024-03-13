import logging

from openai import OpenAI as OpenAIClient

from .ml_provider import MLProvider


class OpenAI(MLProvider):
    def __init__(self, api_key: str, generative_model: str):
        self._client = OpenAIClient(api_key=api_key)
        self._generative_model = generative_model

    def check_api_key(self) -> bool:
        success = False
        try:
            success = self._client.models.list() is not None
        except Exception:
            logging.exception("OpenAI API key check failed.")
        return success

    def get_valid_models(self) -> list:
        models = []
        try:
            models = self._client.models.list()
        except Exception:
            logging.exception("OpenAI model list retrieval failed.")
        return models

    def check_model(self) -> bool:
        success = False
        try:
            success = self._client.models.retrieve(self._generative_model) is not None
        except Exception:
            logging.exception("OpenAI model check failed.")
        return success

    def completion(self, prompt: str) -> str:
        completion = self._client.chat.completions.create(
            model=self._generative_model,
            messages=[{"role": "user", "content": prompt}],
        )
        message = completion.choices[0].message.content
        return message
