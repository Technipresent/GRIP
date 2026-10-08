"""Frozen contracts between SYNC and GRIP. Version 2.0. Changing a field means a new version."""
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

CONTRACT_VERSION = "2.0"


class Verdict(str, Enum):
    SUPPORTED = "Supported"
    CONTRADICTED = "Contradicted"
    DISPUTED = "Disputed"
    NO_EVIDENCE = "No evidence it exists"


class Claim(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=2000)
    subject: str = Field(min_length=1, max_length=300)
    context: str = Field(default="", max_length=8000)
    stakes: Literal["normal", "high"] = "normal"


class GroundRequest(BaseModel):
    contract_version: Literal["2.0"] = CONTRACT_VERSION
    claims: list[Claim] = Field(min_length=1, max_length=200)

    @field_validator("claims")
    @classmethod
    def unique_ids(cls, claims):
        ids = [c.id for c in claims]
        if len(ids) != len(set(ids)):
            raise ValueError("claim ids must be unique")
        return claims


class Quote(BaseModel):
    text: str
    url: str
    providers: list[str]


class CheckerScore(BaseModel):
    checker: str
    score: float | None
    url: str


class ClaimResult(BaseModel):
    id: str
    verdict: Verdict
    deciding_rule: str
    quotes: list[Quote]
    checker_scores: list[CheckerScore]
    confidence: float = Field(ge=0.0, le=1.0)


class GroundResponse(BaseModel):
    contract_version: Literal["2.0"] = CONTRACT_VERSION
    results: list[ClaimResult]
