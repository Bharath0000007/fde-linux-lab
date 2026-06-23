from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

log = logging.getLogger(__name__)


# ■■ TASK 1A: ShipmentOrder input model ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■


class ShipmentOrder(BaseModel):
    """Validates a raw shipment order from the API."""

    order_id: str = Field(..., min_length=3)
    order_type: Literal["shipment"]

    carrier_code: str = Field(..., min_length=2, max_length=10)

    origin: str = Field(..., min_length=2)
    destination: str = Field(..., min_length=2)

    delay_days: int = Field(default=0, ge=0)
    cost_usd: float = Field(..., gt=0)

    priority: Literal[
        "standard",
        "express",
        "critical",
    ] = "standard"

    tags: list[str] = Field(default_factory=list)

    model_config = {
        "str_strip_whitespace": True,
        "extra": "ignore",
    }

    @field_validator("carrier_code")
    @classmethod
    def normalise_carrier(cls, v: str) -> str:
        v = v.upper()

        if not v.isalnum():
            raise ValueError("carrier_code must contain only letters and digits")

        return v

    @model_validator(mode="after")
    def check_route(self) -> "ShipmentOrder":
        if self.origin.lower() == self.destination.lower():
            raise ValueError("origin and destination must differ")

        return self


# ■■ TASK 1B: EquipmentOrder input model ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■


class EquipmentOrder(BaseModel):
    """Validates a raw equipment asset registration."""

    order_id: str = Field(..., min_length=3)

    order_type: Literal["equipment"]

    model_name: str = Field(..., min_length=2)

    purchase_price: float = Field(..., gt=0)

    age_years: float = Field(..., ge=0)

    location: str

    owner: str = "AutoFinance Bank"

    model_config = {
        "str_strip_whitespace": True,
        "extra": "ignore",
    }

    @field_validator("age_years")
    @classmethod
    def validate_age(cls, v: float) -> float:
        if v > 30:
            raise ValueError(f"age_years {v} unreasonably high (max 30)")

        return round(v, 1)


# ■■ TASK 2: Abstract base + subclasses ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■


class Asset(ABC):
    """Abstract base for all supply chain assets."""

    def __init__(
        self,
        order_id: str,
        owner: str,
    ) -> None:
        self.order_id = order_id
        self.owner = owner
        self.created_at = datetime.utcnow()

    @abstractmethod
    def process(self) -> dict:
        """Process the asset and return a Foundry-ready record."""
        ...

    @abstractmethod
    def estimated_value(self) -> float:
        """Return estimated current value in USD."""
        ...

    def asset_type(self) -> str:
        return self.__class__.__name__.lower()


class ProcessedShipment(Asset):
    """A validated, processed shipment asset."""

    PENALTY_RATE = 150.0

    def __init__(
        self,
        order: ShipmentOrder,
    ) -> None:
        super().__init__(
            order.order_id,
            "AutoFinance Bank",
        )

        self.order = order

    def estimated_value(self) -> float:
        # Shipments: cargo value not tracked
        return 0.0

    def process(self) -> dict:
        penalty_usd = self.order.delay_days * self.PENALTY_RATE

        return {
            "order_id": self.order.order_id,
            "asset_type": self.asset_type(),
            "carrier_code": self.order.carrier_code,
            "origin": self.order.origin,
            "destination": self.order.destination,
            "status": "processed",
            "delay_days": self.order.delay_days,
            "cost_usd": self.order.cost_usd,
            "penalty_usd": penalty_usd,
            "priority": self.order.priority,
            "tags": ",".join(self.order.tags),
            "processed_at": datetime.utcnow().isoformat(),
        }


class ProcessedEquipment(Asset):
    """A validated, processed equipment asset."""

    DEPRECIATION_YEARS = 10

    def __init__(
        self,
        order: EquipmentOrder,
    ) -> None:
        super().__init__(
            order.order_id,
            order.owner,
        )

        self.order = order

    def estimated_value(self) -> float:
        remaining_ratio = max(
            0.0,
            (self.DEPRECIATION_YEARS - self.order.age_years) / self.DEPRECIATION_YEARS,
        )

        return round(
            self.order.purchase_price * remaining_ratio,
            2,
        )

    def process(self) -> dict:
        return {
            "order_id": self.order.order_id,
            "asset_type": self.asset_type(),
            "model_name": self.order.model_name,
            "location": self.order.location,
            "owner": self.order.owner,
            "purchase_price": self.order.purchase_price,
            "age_years": self.order.age_years,
            "current_value": self.estimated_value(),
            "processed_at": datetime.utcnow().isoformat(),
        }


# ■■ TASK 3A: Asset factory ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■


class AssetFactory:
    """Create correct Asset subclass from a validated order."""

    @staticmethod
    def create(
        order: ShipmentOrder | EquipmentOrder,
    ) -> Asset:
        if isinstance(order, ShipmentOrder):
            return ProcessedShipment(order)

        if isinstance(order, EquipmentOrder):
            return ProcessedEquipment(order)

        raise ValueError(f"Unsupported order type: {type(order)}")


# ■■ TASK 3B: Processing result dataclass ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■


@dataclass
class ProcessingResult:
    """Holds the output of a full processing run."""

    processed: list[dict] = field(default_factory=list)

    rejected: list[dict] = field(default_factory=list)

    started_at: datetime = field(default_factory=datetime.utcnow)

    finished_at: Optional[datetime] = None

    @property
    def total_input(self) -> int:
        return len(self.processed) + len(self.rejected)

    @property
    def success_rate_pct(self) -> float:
        if self.total_input == 0:
            return 0.0

        return round(
            len(self.processed) / self.total_input * 100,
            1,
        )

    def summary(self) -> dict:
        return {
            "total_input": self.total_input,
            "processed_count": len(self.processed),
            "rejected_count": len(self.rejected),
            "success_rate_pct": self.success_rate_pct,
            "duration_seconds": (
                (self.finished_at - self.started_at).total_seconds()
                if self.finished_at
                else None
            ),
        }


# ■■ TASK 3C: OrderProcessingEngine ■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■


class OrderProcessingEngine:
    """
    Validates and processes a batch of raw order dicts.
    """

    def run(
        self,
        raw_orders: list[dict],
    ) -> ProcessingResult:

        result = ProcessingResult()

        log.info(
            "Starting processing run: %d orders",
            len(raw_orders),
        )

        for raw in raw_orders:
            order_id = raw.get(
                "order_id",
                "UNKNOWN",
            )

            order_type = raw.get(
                "order_type",
                "",
            )

            try:
                # Step 1: Validate
                order: ShipmentOrder | EquipmentOrder

                if order_type == "shipment":
                    order = ShipmentOrder(**raw)

                elif order_type == "equipment":
                    order = EquipmentOrder(**raw)

                else:
                    raise ValueError(f"Unknown order_type: {order_type!r}")

                # Step 2: Process
                asset = AssetFactory.create(order)

                record = asset.process()

                result.processed.append(record)

                log.info(
                    "Processed %s (%s)",
                    order_id,
                    order_type,
                )

            except ValidationError as e:
                errors = []

                for err in e.errors():
                    loc = err.get("loc", ())

                    field = loc[0] if loc else "check_route"

                    errors.append(f"{field}: {err['msg']}")

                result.rejected.append({"order_id": order_id, "errors": errors})

                log.warning("Validation failed for %s: %s", order_id, errors)

            except Exception as e:
                result.rejected.append(
                    {
                        "order_id": order_id,
                        "errors": [str(e)],
                    }
                )

                log.warning(
                    "Validation failed for %s: %s",
                    order_id,
                    [str(e)],
                )

        result.finished_at = datetime.utcnow()

        log.info(
            "Processing complete: %s",
            result.summary(),
        )

        return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=("%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"),
        datefmt="%H:%M:%S",
    )

    raw_orders = [
        {
            "order_id": "ORD-001",
            "order_type": "shipment",
            "carrier_code": "dhl",
            "origin": "Mumbai",
            "destination": "Delhi",
            "delay_days": 3,
            "cost_usd": 250.0,
            "priority": "express",
            "tags": ["urgent", "fragile"],
        },
        {
            "order_id": "ORD-002",
            "order_type": "equipment",
            "model_name": "Forklift XR500",
            "purchase_price": 45000.0,
            "age_years": 4.5,
            "location": "Chennai Warehouse",
        },
        {
            "order_id": "ORD-003",
            "order_type": "shipment",
            "carrier_code": "FEDEX",
            "origin": "Mumbai",
            "destination": "Mumbai",
            "cost_usd": 180.0,
        },
        {
            "order_id": "ORD-004",
            "order_type": "shipment",
            "carrier_code": "BDT",
            "origin": "Pune",
            "destination": "Hyderabad",
            "cost_usd": -50.0,
        },
        {
            "order_id": "ORD-005",
            "order_type": "vehicle",
            "carrier_code": "DHL",
            "cost_usd": 100.0,
        },
        {
            "order_id": "ORD-006",
            "order_type": "equipment",
            "model_name": "Conveyor Belt MK3",
            "purchase_price": 22000.0,
            "age_years": 9.0,
            "location": "Bengaluru Plant",
        },
    ]

    engine = OrderProcessingEngine()

    result = engine.run(raw_orders)

    print("\n" + "=" * 50)
    print("PROCESSING SUMMARY")
    print("=" * 50)

    for k, v in result.summary().items():
        print(f"{k:<25} {v}")

    print("\nPROCESSED RECORDS:")

    for rec in result.processed:
        print(
            f"[{rec['asset_type'].upper()}] "
            f"{rec['order_id']} "
            f"| value=${rec.get('current_value', rec.get('cost_usd', 0)):,.2f}"
        )

    print("\nREJECTED RECORDS:")

    for rej in result.rejected:
        print(f"{rej['order_id']}: {rej['errors']}")
