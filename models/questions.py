from typing import Literal

from pydantic import BaseModel


class Question(BaseModel):
    id: int
    mode: Literal["single_choice", "multiple_choice"]
    question: str
    options: list[str]
    answer: int | list[int]  # index of the correct option
    explanation: str | None = None
    domain: str = "ML Fundamentals & Theory"
    gcp_products: list[str] = []
    gcp_topics: list[str] = []
    ml_topics: list[str] = []
