
import logging
import asyncio
import requests

import google.generativeai as genai

from google.generativeai.types import RequestOptions
from google.api_core.exceptions import (
    ServiceUnavailable,
    TooManyRequests,
    DeadlineExceeded,
    InternalServerError,
)

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

NVIDIA_CHAT_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

NVIDIA_CHAT_MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"

MAX_GEMINI_RETRIES = 2


# ==========================================
# NVIDIA GENERATION (REST API)
# ==========================================

async def generate_nvidia(prompt: str):

    logger.warning("Basculement vers NVIDIA AI...")

    def make_request():
        payload = {
            "model": NVIDIA_CHAT_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": 1042,
            "stream": False
        }

        response = requests.post(
            NVIDIA_CHAT_URL,
            headers={
                "Authorization": f"Bearer {settings.nvidia_api_key}",
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=90
        )

        response.raise_for_status()
        return response.json()

    # requests est synchrone : on l'exécute dans un thread
    data = await asyncio.to_thread(make_request)

    answer = data["choices"][0]["message"]["content"]

    if not answer:
        raise RuntimeError("NVIDIA n'a retourné aucune réponse")

    total_tokens = data.get("usage", {}).get("total_tokens", 0)

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
                f"Gemini génération - tentative "
                f"{attempt + 1}/{MAX_GEMINI_RETRIES}"
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

            logger.warning(f"Gemini indisponible : {e}")

            if attempt < MAX_GEMINI_RETRIES - 1:
                await asyncio.sleep(2)

        except Exception:
            logger.exception("Erreur inattendue Gemini")
            raise

    # ======================================
    # GEMINI FAILED -> NVIDIA FALLBACK
    # ======================================

    logger.warning(
        "Gemini indisponible. Activation du fallback NVIDIA."
    )

    try:
        return await generate_nvidia(prompt)

    except Exception:
        logger.exception("Gemini et NVIDIA sont indisponibles")
        raise RuntimeError(
            "Les services IA Gemini et NVIDIA sont "
            "temporairement indisponibles."
        )
