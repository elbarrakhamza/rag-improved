import google.generativeai as genai
from app.core.config import settings

genai.configure(api_key=settings.google_api_key)

gemini=genai.GenerativeModel(
    model_name='gemini-3.1-flash-lite',
    generation_config={
        "temperature":.1,
    }
)

async def generate(prompt:str):
    response= await gemini.generate_content_async(prompt)
    answer=response.text
    total_tokens=response.usage_metadata.total_token_count
    return answer,total_tokens