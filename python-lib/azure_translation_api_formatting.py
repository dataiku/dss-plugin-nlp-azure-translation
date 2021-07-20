# -*- coding: utf-8 -*-
"""Module with classes to format results from the Azure Translation API"""

import logging
from typing import AnyStr
from typing import Dict
from typing import List

import pandas as pd

from plugin_io_utils import API_COLUMN_NAMES_DESCRIPTION_DICT
from plugin_io_utils import ErrorHandlingEnum
from plugin_io_utils import build_unique_column_names
from plugin_io_utils import generate_unique
from plugin_io_utils import safe_json_loads
from plugin_io_utils import move_api_columns_to_end


LANGUAGE_CODE_LABELS = {
    "af": "Afrikaans",
    "am": "Amharic",
    "ar": "Arabic",
    "as": "Assamese",
    "az": "Azerbaijani",
    "bg": "Bulgarian",
    "bn": "Bangla",
    "bs": "Bosnian",
    "ca": "Catalan",
    "cs": "Czech",
    "cy": "Welsh",
    "da": "Danish",
    "de": "German",
    "el": "Greek",
    "en": "English",
    "es": "Spanish",
    "et": "Estonian",
    "fa": "Persian",
    "fi": "Finnish",
    "fil": "Filipino",
    "fj": "Fijian",
    "fr": "French",
    "fr-CA": "French (Canada)",
    "ga": "Irish",
    "gu": "Gujarati",
    "he": "Hebrew",
    "hi": "Hindi",
    "hr": "Croatian",
    "ht": "Haitian Creole",
    "hu": "Hungarian",
    "hy": "Armenian",
    "id": "Indonesian",
    "is": "Icelandic",
    "it": "Italian",
    "iu": "Inuktitut",
    "ja": "Japanese",
    "kk": "Kazakh",
    "km": "Khmer",
    "kmr": "Kurdish (Northern)",
    "kn": "Kannada",
    "ko": "Korean",
    "ku": "Kurdish (Central)",
    "lo": "Lao",
    "lt": "Lithuanian",
    "lv": "Latvian",
    "mg": "Malagasy",
    "mi": "Maori",
    "ml": "Malayalam",
    "mr": "Marathi",
    "ms": "Malay",
    "mt": "Maltese",
    "mww": "Hmong Daw",
    "my": "Myanmar (Burmese)",
    "nb": "Norwegian",
    "ne": "Nepali",
    "nl": "Dutch",
    "or": "Odia",
    "otq": "Querétaro Otomi",
    "pa": "Punjabi",
    "pl": "Polish",
    "prs": "Dari",
    "ps": "Pashto",
    "pt": "Portuguese (Brazil)",
    "pt-PT": "Portuguese (Portugal)",
    "ro": "Romanian",
    "ru": "Russian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "sm": "Samoan",
    "sq": "Albanian",
    "sr-Cyrl": "Serbian (Cyrillic)",
    "sr-Latn": "Serbian (Latin)",
    "sv": "Swedish",
    "sw": "Swahili",
    "ta": "Tamil",
    "te": "Telugu",
    "th": "Thai",
    "ti": "Tigrinya",
    "tlh-Latn": "Klingon (Latin)",
    "tlh-Piqd": "Klingon (pIqaD)",
    "to": "Tongan",
    "tr": "Turkish",
    "ty": "Tahitian",
    "uk": "Ukrainian",
    "ur": "Urdu",
    "vi": "Vietnamese",
    "yua": "Yucatec Maya",
    "yue": "Cantonese (Traditional)",
    "zh-Hans": "Chinese Simplified",
    "zh-Hant": "Chinese Traditional",
}

# ==============================================================================
# CLASS AND FUNCTION DEFINITION
# ==============================================================================


class GenericAPIFormatter:
    """
    Generic Formatter class for API responses:
    - initialize with generic parameters
    - compute generic column descriptions
    - apply format_row to dataframe
    """

    def __init__(
        self,
        input_df: pd.DataFrame,
        column_prefix: AnyStr = "api",
        error_handling: ErrorHandlingEnum = ErrorHandlingEnum.LOG,
    ):
        self.input_df = input_df
        self.column_prefix = column_prefix
        self.error_handling = error_handling
        self.api_column_names = build_unique_column_names(input_df, column_prefix)
        self.column_description_dict = {
            v: API_COLUMN_NAMES_DESCRIPTION_DICT[k]
            for k, v in self.api_column_names._asdict().items()
        }

    def format_row(self, row: Dict) -> Dict:
        return row

    def format_df(self, df: pd.DataFrame) -> pd.DataFrame:
        logging.info("Formatting API results...")
        df = df.apply(func=self.format_row, axis=1)
        df = move_api_columns_to_end(df, self.api_column_names, self.error_handling)
        logging.info("Formatting API results: Done.")
        return df


class TranslationAPIFormatter(GenericAPIFormatter):
    """
    Formatter class for translation API responses:
    - make sure response is valid JSON
    """

    def __init__(
        self,
        input_df: pd.DataFrame,
        input_column: AnyStr,
        target_language: AnyStr,
        source_language: AnyStr = None,
        column_prefix: AnyStr = "translation_api",
        error_handling: ErrorHandlingEnum = ErrorHandlingEnum.LOG,
    ):
        super().__init__(input_df, column_prefix, error_handling)
        self.translated_text_column_name = generate_unique(
            f"{input_column}_{target_language.replace('-', '_')}", input_df.columns, prefix=None
        )
        self.detected_language_column_name = generate_unique(
            f"{input_column}_language", input_df.columns, prefix=None
        )
        self.source_language = source_language
        self.input_column = input_column
        self.input_df_columns = input_df.columns
        self.target_language = target_language
        self.target_language_label = LANGUAGE_CODE_LABELS[self.target_language]
        self._compute_column_description()

    def _compute_column_description(self):
        self.column_description_dict[
            self.translated_text_column_name
        ] = f"{self.target_language_label} translation of the '{self.input_column}' column by Azure Translation"
        if not self.source_language:
            self.column_description_dict[
                self.detected_language_column_name
            ] = f"Detected language of the '{self.input_column}' column by Azure Translation"

    def format_row(self, row: Dict) -> Dict:
        raw_response = row[self.api_column_names.response]
        response = safe_json_loads(raw_response, self.error_handling)
        # Azure returns a one-element list when the request is successful
        if isinstance(response, List):
            response = response[0]
        # Extract the detected source language & translated text with get statements assuring
        # that in case the response is empty an empty string is returned
        if not self.source_language:
            row[self.detected_language_column_name] = LANGUAGE_CODE_LABELS.get(
                response.get("detectedLanguage", {}).get("language", ""), ""
            )
        row[self.translated_text_column_name] = response.get("translations", [{}])[0].get(
            "text", ""
        )
        return row
