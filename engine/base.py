from abc import ABC, abstractmethod
from api.models.schemas import VerdictResponse, QuestionMeta


class BaseQuestion(ABC):
    """
    Every question module implements this interface.
    run() pulls from the DB/marts, applies rules, and returns a VerdictResponse.
    """

    @abstractmethod
    def meta(self) -> QuestionMeta:
        ...

    @abstractmethod
    def run(self) -> VerdictResponse:
        ...
