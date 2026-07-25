from enum import Enum

from pydantic import BaseModel


class Category(str, Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    UNCLEAR = "unclear"


class InsightKind(str, Enum):
    STRENGTH = "strength"
    GAP = "gap"


class Responsibility(BaseModel):
    id: str
    text: str
    source_quote: str


class Requirement(BaseModel):
    id: str
    text: str
    category: Category
    source_quote: str


class Posting(BaseModel):
    title: str
    company: str
    location: str
    seniority: str
    responsibilities: list[Responsibility]
    requirements: list[Requirement]

    def all_ids(self) -> set[str]:
        return {r.id for r in self.requirements} | {r.id for r in self.responsibilities}


class Insight(BaseModel):
    id: str
    text: str
    kind: InsightKind
    supporting_ids: list[str]
