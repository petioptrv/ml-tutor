# -*- coding: utf-8 -*-

# ML-Tutor Add-on for Anki
#
# Copyright (C)  2016-2019 Petrov P.
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

import logging
from typing import Dict

import requests

from .ml_provider import MLProvider


class OpenAI(MLProvider):
    _base_url = "https://api.openai.com/v1"

    def __init__(self, api_key: str, generative_model: str):
        self._api_key = api_key
        self._generative_model = generative_model

    def check_connected_to_web(self) -> bool:
        success = False
        try:
            url = f"{self._base_url}/models"
            headers = self._build_auth_headers()
            requests.get(url=url, headers=headers)
            success = True
        except requests.exceptions.ConnectionError:
            pass  #
        except Exception:
            logging.exception("OpenAI API server check failed.")
        return success

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
