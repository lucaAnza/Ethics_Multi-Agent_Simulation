"""Static provider and prompt configuration for LLM decision engines."""

from ethics.config import CONSTANT, KANT, UTILITARIANISM, VIRTUE_ETHICS


DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
MINIMUM_GEMINI_TIMEOUT_SECONDS = 10.0

PROMPT_FILENAMES = {
    UTILITARIANISM: "utilitarianism.yaml",
    KANT: "kant.yaml",
    CONSTANT: "constant.yaml",
    VIRTUE_ETHICS: "virtue_ethics.yaml",
}

