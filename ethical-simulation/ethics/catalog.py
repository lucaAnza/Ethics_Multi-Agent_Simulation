"""Canonical catalog of ethical frameworks and supported implementations."""

from decision_engine.modes import CODE_MODE, LLM_MODE


UTILITARIANISM = "Utilitarianism"
KANT = "Kant"
CONSTANT = "Constant"
VIRTUE_ETHICS = "Virtue Ethics"

FRAMEWORK_IMPLEMENTATIONS = {
    UTILITARIANISM: (CODE_MODE, LLM_MODE),
    KANT: (CODE_MODE, LLM_MODE),
    CONSTANT: (CODE_MODE, LLM_MODE),
    VIRTUE_ETHICS: (LLM_MODE,),
}

FRAMEWORKS = tuple(FRAMEWORK_IMPLEMENTATIONS)
DETERMINISTIC_FRAMEWORKS = tuple(
    name
    for name, implementations in FRAMEWORK_IMPLEMENTATIONS.items()
    if CODE_MODE in implementations
)
LLM_FRAMEWORKS = frozenset(
    name
    for name, implementations in FRAMEWORK_IMPLEMENTATIONS.items()
    if LLM_MODE in implementations
)
FRAMEWORK_OPTIONS = tuple(
    f"{framework_name} ({implementation})"
    for framework_name, implementations in FRAMEWORK_IMPLEMENTATIONS.items()
    for implementation in implementations
)
