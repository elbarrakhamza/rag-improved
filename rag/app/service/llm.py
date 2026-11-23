import logging
import google.generativeai as genai

from google.generativeai.types import RequestOptions
from app.core.config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.google_api_key)

gemini = genai.GenerativeModel(
    model_name="gemini-3.1-flash-lite",
    generation_config={
        "temperature": 0.1,
        "max_output_tokens": 1042,
    }
)


async def generate(prompt: str):
    try:
        logger.info("Début génération Gemini")

        response = await gemini.generate_content_async(
            prompt,
            request_options=RequestOptions(timeout=90)
        )

        if not response.candidates:
            raise RuntimeError("Gemini n'a retourné aucun candidat")

        answer = response.text

        usage = response.usage_metadata
        total_tokens = usage.total_token_count if usage else 0

        logger.info(
            f"Génération Gemini terminée - Tokens: {total_tokens}"
        )

        return answer, total_tokens

    except Exception:
        logger.exception("Erreur pendant la génération Gemini")
        raise