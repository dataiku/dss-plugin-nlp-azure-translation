# -*- coding: utf-8 -*-
import json
from typing import AnyStr
from typing import Dict

import dataiku
from dataiku.customrecipe import get_input_names_for_role
from dataiku.customrecipe import get_output_names_for_role
from dataiku.customrecipe import get_recipe_config

from azure_translation_api_client import API_EXCEPTIONS
from azure_translation_api_client import AzureTranslatorClient
from azure_translation_api_formatting import TranslationAPIFormatter
from dku_io_utils import set_column_description
from plugin_io_utils import ErrorHandlingEnum
from plugin_io_utils import validate_column_input
from retry import retry

from parallelizer import DataFrameParallelizer

# ==============================================================================
# SETUP
# ==============================================================================

api_configuration_preset = get_recipe_config().get("api_configuration_preset")
if api_configuration_preset is None or api_configuration_preset == {}:
    raise ValueError("Please specify an API configuration preset")

# Recipe parameters
text_column = get_recipe_config().get("text_column")
target_language = get_recipe_config().get("target_language", "")
# For auto-translate Azure takes an empty string for the source language
source_language = get_recipe_config().get("source_language", "").replace("auto", "")

# Params for parallelization
column_prefix = "translation_api"
parallel_workers = api_configuration_preset.get("parallel_workers")
error_handling = (
    ErrorHandlingEnum.FAIL if get_recipe_config().get("fail_on_error") else ErrorHandlingEnum.LOG
)

# Params for translation
client = AzureTranslatorClient(
    api_configuration_preset.get("azure_api_key"), api_configuration_preset.get("azure_location")
)
max_attempts = api_configuration_preset.get("max_attempts")
wait_interval = api_configuration_preset.get("wait_interval")


# ==============================================================================
# DEFINITIONS
# ==============================================================================

input_dataset = dataiku.Dataset(get_input_names_for_role("input_dataset")[0])
output_dataset = dataiku.Dataset(get_output_names_for_role("output_dataset")[0])
validate_column_input(text_column, [col["name"] for col in input_dataset.read_schema()])
input_df = input_dataset.get_dataframe()


@retry((API_EXCEPTIONS), delay=wait_interval, tries=max_attempts)
def call_translation_api(
    row: Dict,
    text_column: AnyStr,
    target_language: AnyStr,
    source_language: AnyStr = None,
    split_sentences: AnyStr = "1",
    preserve_formatting: AnyStr = "0",
    formality: AnyStr = "default",
) -> AnyStr:
    """
    Calls DeepL Translation API. No Source language means Autodetect.
    """
    text = row[text_column]
    if not isinstance(text, str) or text.strip() == "":
        return json.dumps({})
    else:
        response = client.translate(
            text,
            target_language,
            source_language=source_language,
        )
        return response


formatter = TranslationAPIFormatter(
    input_df=input_df,
    input_column=text_column,
    target_language=target_language,
    source_language=source_language,
    column_prefix=column_prefix,
    error_handling=error_handling,
)

# ==============================================================================
# RUN
# ==============================================================================

df_parallelizer = DataFrameParallelizer(
    function=call_translation_api,
    error_handling=error_handling,
    exceptions_to_catch=API_EXCEPTIONS,
    parallel_workers=parallel_workers,
    output_column_prefix=column_prefix,
)

df = df_parallelizer.run(
    input_df,
    text_column=text_column,
    target_language=target_language,
    source_language=source_language,
)

output_df = formatter.format_df(df)
output_dataset.write_with_schema(output_df)

set_column_description(
    input_dataset=input_dataset,
    output_dataset=output_dataset,
    column_description_dict=formatter.column_description_dict,
)
