
import logging
import asyncio
import os

import google.generativeai as genai
from google.generativeai.types import RequestOptions

from google.api_core.exceptions import (
    ServiceUnavailable,
    TooManyRequests,
    DeadlineExceeded,
    InternalServerError,
)

from openai import AsyncOpenAI, APIError

from app.core.config import settings

logger = logging.getLogger(__name__)

# ==========================================
# GOOGLE GEMINI - PRIMARY LLM
# ==========================================

genai.configure(api_key=settings.google_api_key)

gemini = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    generation_config={
        "temperature": 0.1,
        "max_output_tokens": 1024,
    }
)

# ==========================================
# NVIDIA AI - FALLBACK LLM
# ==========================================

nvidia = AsyncOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=settings.nvidia_api_key,
    timeout=90.0,
)

NVIDIA_MODEL = os.getenv(
    "NVIDIA_CHAT_MODEL",
    "nvidia/nemotron-3.5-lightning-30b-a3b"
)

MAX_GEMINI_RETRIES = 2


# ==========================================
# NVIDIA GENERATION
# ==========================================

async def generate_nvidia(prompt: str):

    logger.warning("Basculement vers NVIDIA AI...")

    response = await nvidia.chat.completions.create(
        model=NVIDIA_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_tokens=1042,
        stream=False,
    )

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError("NVIDIA n'a retourné aucune réponse")

    total_tokens = (
        response.usage.total_tokens
        if response.usage
        else 0
    )

    logger.info(
        f"NVIDIA AI génération réussie - Tokens: {total_tokens}"
    )

    return answer, total_tokens


# ==========================================
# MAIN GENERATION
# GEMINI -> NVIDIA FALLBACK
# ==========================================

async def generate(prompt: str):

    for attempt in range(MAX_GEMINI_RETRIES):

        try:
            logger.info(
                f"Gemini génération - tentative {attempt + 1}/"
                f"{MAX_GEMINI_RETRIES}"
            )

            response = await gemini.generate_content_async(
                prompt,
                request_options=RequestOptions(timeout=45)
            )

            if not response.candidates:
                raise RuntimeError(
                    "Gemini n'a retourné aucun candidat"
                )

            answer = response.text

            if not answer:
                raise RuntimeError(
                    "Gemini a retourné une réponse vide"
                )

            usage = response.usage_metadata
            total_tokens = (
                usage.total_token_count if usage else 0
            )

            logger.info(
                f"Gemini génération réussie - Tokens: {total_tokens}"
            )

            return answer, total_tokens

        except (
            ServiceUnavailable,
            TooManyRequests,
            DeadlineExceeded,
            InternalServerError,
            asyncio.TimeoutError,
        ) as e:

            logger.warning(
                f"Gemini indisponible : {e}"
            )

            if attempt < MAX_GEMINI_RETRIES - 1:
                await asyncio.sleep(2)

    # ======================================
    # GEMINI FAILED -> NVIDIA FALLBACK
    # ======================================

    logger.warning(
        "Gemini indisponible après plusieurs tentatives. "
        "Activation du fallback NVIDIA."
    )

    try:
        return await generate_nvidia(prompt)

    except (APIError, Exception):
        logger.exception(
            "Gemini et NVIDIA sont indisponibles"
        )
        raise RuntimeError(
            "Les services IA Gemini et NVIDIA sont "
            "temporairement indisponibles."
        )
