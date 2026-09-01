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


# Canonical moral-rule keys. Rule implementations use these same constants, so
# their identifiers and the configurable default orders cannot drift apart.
DO_NOT_REDIRECT_HARM = "do_not_redirect_harm"
IGNORE_PERSONAL_CATEGORIES = "ignore_personal_categories"
IGNORE_NUMERICAL_DIFFERENCES = "ignore_numerical_differences"
PREFER_STAY_WHEN_UNRESOLVED = "prefer_stay_when_unresolved"
DO_NOT_INCREASE_HARM = "do_not_increase_harm"
ALWAYS_PROTECT_CHILD = "always_protect_child"

# Change the order of these keys to change the default priority order of moral rules.
MORAL_RULE_KEYS = (
    IGNORE_PERSONAL_CATEGORIES,
    IGNORE_NUMERICAL_DIFFERENCES,
    PREFER_STAY_WHEN_UNRESOLVED,
    DO_NOT_INCREASE_HARM,
    DO_NOT_REDIRECT_HARM,
    ALWAYS_PROTECT_CHILD,
)

# Kant evaluates applicable rules in this strict priority order.
DEFAULT_KANT_RULE_ORDER = MORAL_RULE_KEYS
DEFAULT_KANT_RULE_ENABLED = {
    rule_key: True for rule_key in DEFAULT_KANT_RULE_ORDER
}

# Constant gives every rule equal moral weight. This order is used only to keep
# configuration, UI rows and vote collection deterministic; it is not priority.
DEFAULT_CONSTANT_RULE_ORDER = MORAL_RULE_KEYS
DEFAULT_CONSTANT_RULE_ENABLED = {
    rule_key: True for rule_key in DEFAULT_CONSTANT_RULE_ORDER
}
