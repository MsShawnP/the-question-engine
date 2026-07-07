from abc import ABC, abstractmethod
from api.models.schemas import VerdictResponse, QuestionMeta


class NoDataError(RuntimeError):
    """
    Raised by a question's run() when the queries return no usable rows.
    The API layer turns this into a friendly 503 instead of a raw 500.
    """


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
