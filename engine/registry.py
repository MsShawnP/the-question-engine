from engine.base import BaseQuestion


class QuestionRegistry:
    def __init__(self) -> None:
        self._questions: dict[str, BaseQuestion] = {}

    def register(self, question: BaseQuestion) -> None:
        meta = question.meta()
        self._questions[meta.id] = question

    def get(self, question_id: str) -> BaseQuestion | None:
        return self._questions.get(question_id)

    def all(self) -> list[BaseQuestion]:
        return list(self._questions.values())


registry = QuestionRegistry()

# Auto-register all question modules on import
from engine.questions import q01_biggest_customer  # noqa: E402, F401
from engine.questions import q02_retailer_launch_cost  # noqa: E402, F401
from engine.questions import q03_sku_rationalization  # noqa: E402, F401
from engine.questions import q04_trade_spend  # noqa: E402, F401
from engine.questions import q05_edi_reconciliation  # noqa: E402, F401
from engine.questions import q06_recall_cost  # noqa: E402, F401
from engine.questions import q07_product_data_preflight  # noqa: E402, F401
from engine.questions import q08_weight_cost  # noqa: E402, F401
from engine.questions import q09_channel_profitability  # noqa: E402, F401
from engine.questions import q10_deduction_recovery  # noqa: E402, F401
from engine.questions import q11_stockout_cost  # noqa: E402, F401
from engine.questions import q12_forecast_accuracy  # noqa: E402, F401
from engine.questions import q13_otif_exposure  # noqa: E402, F401
from engine.questions import q14_velocity_decay  # noqa: E402, F401
from engine.questions import q15_cash_conversion  # noqa: E402, F401
