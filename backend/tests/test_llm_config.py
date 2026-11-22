import unittest
from unittest.mock import patch

from core.config import settings
from core.integrations.llm import configured, create_llm, model_name


class ModelConfigTests(unittest.TestCase):
    def test_placeholder_keys_are_not_configured(self):
        for key in ["", "placeholder", "none", "your-google-api-key-here"]:
            self.assertFalse(configured(key))

    def test_effective_google_model(self):
        with patch.object(settings, "OPENROUTER_API_KEY", ""), patch.object(settings, "LLM_MODEL", "provider/model"), patch.object(settings, "GOOGLE_MODEL", "gemini-test"):
            self.assertEqual(model_name(), "gemini-test")

    def test_missing_credentials_fail_before_provider_call(self):
        with patch.object(settings, "OPENROUTER_API_KEY", ""), patch.object(settings, "GOOGLE_API_KEY", ""):
            with self.assertRaisesRegex(ValueError, "Configure"):
                create_llm(temperature=0, max_tokens=50)

    def test_openrouter_configuration_is_shared(self):
        with patch.object(settings, "OPENROUTER_API_KEY", "test-key"), patch.object(settings, "LLM_MODEL", "provider/test"), patch("langchain_openai.ChatOpenAI") as factory:
            create_llm(temperature=0, max_tokens=50)
        self.assertEqual(factory.call_args.kwargs["model"], "provider/test")
        self.assertEqual(factory.call_args.kwargs["api_key"], "test-key")
        self.assertEqual(factory.call_args.kwargs["timeout"], settings.CHAT_TIMEOUT_SECONDS)

    def test_final_writer_can_disable_optional_reasoning(self):
        with patch.object(settings, "OPENROUTER_API_KEY", "test-key"), patch("langchain_openai.ChatOpenAI") as factory:
            create_llm(temperature=0.7, max_tokens=1500, reasoning=False)
        self.assertEqual(factory.call_args.kwargs["extra_body"], {"reasoning": {"enabled": False}})


if __name__ == "__main__":
    unittest.main()
