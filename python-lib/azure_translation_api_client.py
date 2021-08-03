# -*- coding: utf-8 -*-
"""Module with utility functions to call the Azure Translator API"""

import json
import logging
import re
from typing import AnyStr

import requests

# ==============================================================================
# CONSTANT DEFINITION
# ==============================================================================


API_EXCEPTIONS = (requests.HTTPError,)


# ==============================================================================
# CLASS AND FUNCTION DEFINITION
# ==============================================================================


class AzureTranslatorClient:
    """
    Translation client interfacing with the Azure Translator.

    Args:
        api_key: Azure Translator API Key
        location: Azure location, e.g. francecentral

    """

    def __init__(self, api_key, location) -> None:
        self.api_key = api_key
        self.location = location

        self.endpoint = "https://api.cognitive.microsofttranslator.com/translate"

    def translate(
        self,
        text: AnyStr,
        target_language: AnyStr,
        source_language: AnyStr = None,
    ) -> AnyStr:
        """
        Translates text.

        Args:
            text: Text to be translated
            target_language: Code of the language into which the text should be translated
            source_language: Code of the language of the text to be translated

        Returns:
            response.text: JSON string with the API response.

        Raises:
            HTTPError: An error occured accessing the API.
        """
        response = requests.post(
            url=self.endpoint,
            headers={
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Ocp-Apim-Subscription-Region": self.location,
                "Content-type": "application/json",
            },
            params={"api-version": "3.0", "from": source_language, "to": target_language},
            data={
                "source_lang": source_language,
                "target_lang": target_language,
                "auth_key": self.api_key,
                "text": text,
            },
        )
        if response.status_code == requests.codes.ok:
            # Returns text from the response object which is a json string, so no need to dump it into json anymore
            return response.text
        else:
            # Extracts error related information
            # Azure Translator returns errors of the form
            # {
            #    "error": {
            #        "code": 401000,
            #        "message": "The request is not authorized because credentials are missing or invalid."
            #    }
            # }
            error_dict = json.loads(response.text).get("error", {})

            user_message = (
                "Encountered the following error while sending an API request to Azure:"
                + f" HTTP Error Code: {response.status_code}"
                + f" Azure Code: {error_dict.get('code', '')}"
                + f" Azure Message: {error_dict.get('message', '')}"
            )

            raise requests.HTTPError(user_message)
