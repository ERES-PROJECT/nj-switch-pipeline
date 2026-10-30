"""Small validated interchange models; database migration is intentionally deferred."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Query(BaseModel):
    supplier: str
    utility: str
    commodity: Literal["electric", "gas"]
    zip: str
    url: str
    adapter: str = "default"
    skip_reason: str | None = None

    @field_validator("zip", mode="before")
    @classmethod
    def zip_code(cls, value: object) -> str:
        raw = str(value).strip()
        if not raw.isascii() or not raw.isdigit() or len(raw) not in (4, 5):
            raise ValueError("ZIP must contain four or five ASCII digits")
        return raw.zfill(5)


class Price(BaseModel):
    value: Decimal
    unit: Literal["USD/kWh", "USD/therm", "USD/CCF", "USD/Dth"]
    raw: str


class DocumentRef(BaseModel):
    url: str
    label: str = "Contract document"
    product_id: str | None = None
    offer_key: str | None = None
    discovery_artifact_id: str | None = None


class Offer(BaseModel):
    key: str
    supplier: str
    utility: str
    commodity: Literal["electric", "gas"]
    zip: str
    name: str
    product_id: str | None = None
    price: Price
    rate_structure: Literal["fixed", "variable", "indexed", "hybrid"] | None = None
    term_months: int | None = None
    term_kind: Literal["fixed_term", "month_to_month"] | None = None
    intro_price: Price | None = None
    intro_duration_months: int | None = None
    intro_duration_billing_cycles: int | None = None
    monthly_fee: Decimal | None = None
    enrollment_fee: Decimal | None = None
    cancellation_fee: Decimal | None = None
    fee_terms: dict[str, str] = Field(default_factory=dict)
    incentives: list[str] = Field(default_factory=list)
    renewable_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    renewable_source: str | None = None
    renewable_claim: str | None = None
    tiers: list[dict] = Field(default_factory=list)
    enrollment_url: str | None = None
    documents: list[DocumentRef] = Field(default_factory=list)
    contract_ids: list[str] = Field(default_factory=list)
    source_url: str
    source_kind: str
    artifact_id: str
    captured_at: str = Field(default_factory=utc_now)
    raw_fields: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class Contract(BaseModel):
    id: str
    url: str
    artifact_id: str
    media_type: str
    document_kind: str = "unknown"
    source_urls: list[str] = Field(default_factory=list)
    sections: dict[str, str] = Field(default_factory=dict)
    raw_text: str = ""
    fields: dict = Field(default_factory=dict)
    missing_sections: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: Literal["parsed", "text_extracted", "retained", "partial", "needs_review", "failed"] = "needs_review"
    matched_offer_keys: list[str] = Field(default_factory=list)
    match_method: str | None = None


class CollectionResult(BaseModel):
    schema_version: str = "2.0"
    adapter_version: str = "0.3.0"
    replayed: bool = False
    query: Query
    started_at: str = Field(default_factory=utc_now)
    finished_at: str | None = None
    status: Literal["success", "partial", "empty", "failed", "unsupported", "blocked", "needs_review"] = "failed"
    context_verified: bool = False
    live_data_verified: bool = False
    collection_method: str = "none"
    source_offer_count: int | None = Field(default=None, ge=0)
    source_evidence: dict = Field(default_factory=dict)
    offers: list[Offer] = Field(default_factory=list)
    contracts: list[Contract] = Field(default_factory=list)
    candidates: list[dict] = Field(default_factory=list)
    attempts: list[dict] = Field(default_factory=list)
    artifacts: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    completion_issues: list[str] = Field(default_factory=list)
    errors: list[dict] = Field(default_factory=list)
