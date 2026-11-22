"""Shared provider configuration for both model nodes."""
from core.config import settings


def configured(value: str) -> bool:
    return bool(value) and value.lower() not in {"placeholder", "none"} and not value.startswith("your-")


def model_name() -> str:
    if configured(settings.OPENROUTER_API_KEY):
        return settings.LLM_MODEL
    return settings.LLM_MODEL if settings.LLM_MODEL.startswith("gemini-") else settings.GOOGLE_MODEL


def create_llm(*, temperature: float, max_tokens: int, reasoning: bool | None = None):
    if configured(settings.OPENROUTER_API_KEY):
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name(), api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL, temperature=temperature,
            max_tokens=max_tokens, streaming=True,
            timeout=settings.CHAT_TIMEOUT_SECONDS, max_retries=1,
            extra_body={"reasoning": {"enabled": reasoning}} if reasoning is not None else None,
            default_headers={"HTTP-Referer": "https://github.com/JMADIL/CORE", "X-Title": "Core Agent"},
        )
    if not configured(settings.GOOGLE_API_KEY):
        raise ValueError("Configure OPENROUTER_API_KEY or GOOGLE_API_KEY before chatting")
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=model_name(), google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature, max_output_tokens=max_tokens,
        timeout=settings.CHAT_TIMEOUT_SECONDS, max_retries=1,
    )
