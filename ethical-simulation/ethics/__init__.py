"""Available ethical decision strategies."""

from .base import EthicalFramework
from .constant import ConstantFramework
from .kant import KantFramework
from .ross import RossFramework
from .utilitarian import UtilitarianFramework

__all__ = [
    "EthicalFramework",
    "ConstantFramework",
    "KantFramework",
    "RossFramework",
    "UtilitarianFramework",
]
