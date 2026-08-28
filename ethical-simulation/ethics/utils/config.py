"""Static framework catalog and default ethical settings."""

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

DEFAULT_ENTITIES_VALUES = {
    "man": 10.0,
    "woman": 10.0,
    "old_man": 20.0,
    "old_woman": 20.0,
    "boy": 30.0,
    "girl": 30.0,
}
