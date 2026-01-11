from typing import Literal

from pydantic import BaseModel


class Question(BaseModel):
    id: int
    mode: Literal["single_choice", "multiple_choice"]
    question: str
    options: list[str]
    answer: int | list[int]  # index of the correct option
    explanation: str | None = None
