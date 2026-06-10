from pydantic import BaseModel


class KeyNumber(BaseModel):
    label: str
    value: str
    context: str | None = None


class ChartData(BaseModel):
    type: str  # "bar" | "line" | "scatter"
    title: str
    data: list[dict]
    x_key: str
    y_key: str
    unit: str | None = None


class VerdictResponse(BaseModel):
    question_id: str
    question: str
    verdict: str
    verdict_detail: str
    key_numbers: list[KeyNumber]
    chart: ChartData
    rule_explanation: str
    go_deeper_link: str
    go_deeper_label: str
    scenario: str  # "baseline" | "distressed"
    source_piece: str


class QuestionMeta(BaseModel):
    id: str
    question: str
    short_label: str
    source_piece: str
    go_deeper_link: str
    scenario: str
    is_stub: bool = False
