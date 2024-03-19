import logging
from typing import Dict

import requests

from .ml_provider import MLProvider


class OpenAI(MLProvider):
    _base_url = "https://api.openai.com/v1"

    def __init__(self, api_key: str, generative_model: str):
        self._api_key = api_key
        self._generative_model = generative_model

    def check_api_key(self) -> bool:
        success = False
        try:
            url = f"{self._base_url}/models"
            headers = self._build_auth_headers()
            response = requests.get(url=url, headers=headers)
            success = response.status_code == 200
        except Exception:
            logging.exception("OpenAI API key check failed.")
        return success

    def get_valid_models(self) -> list:
        url = f"{self._base_url}/models"
        headers = self._build_auth_headers()
        response = requests.get(url=url, headers=headers).json()
        models = [model_data["id"] for model_data in response["data"]]
        return models

    def check_model(self) -> bool:
        success = False
        try:
            url = f"{self._base_url}/models/{self._generative_model}"
            headers = self._build_auth_headers()
            response = requests.get(url=url, headers=headers)
            success = response.status_code == 200
        except Exception:
            logging.exception("OpenAI model check failed.")
        return success

    def completion(self, prompt: str) -> str:
        url = f"{self._base_url}/chat/completions"
        headers = self._build_auth_headers()
        headers["Content-Type"] = "application/json"
        message = {
            "role": "user",
            "content": prompt,
        }
        data = {
            "model": self._generative_model,
            "messages": [message],
        }
        response = requests.post(url=url, headers=headers, json=data).json()
        message = response["choices"][0]["message"]["content"]
        return message

    def _build_auth_headers(self) -> Dict:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
        }
        return headers
