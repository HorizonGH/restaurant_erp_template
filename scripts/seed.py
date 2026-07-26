"""
Idempotent database seed for the Restaurant ERP template.

Populates all current modules (catalog + inventory) with realistic data for a
mid-size restaurant operation.

Run:
    uv run python -m scripts.seed
    # or
    uv run python scripts/seed.py

Safe to run multiple times — existing records (matched by unique business keys)
are skipped, not duplicated.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Make sure the project root is on sys.path when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import configure_logging
from app.core.settings import settings
from app.core.shared.infrastructure.database import async_session_factory
from app.modules.catalog.domain.enums import UnitType
from app.modules.catalog.domain.models import (
    Category,
    Ingredient,
    Supplier,
    SupplierIngredient,
    UnitOfMeasure,
)
from app.modules.inventory.application.schemas import (
    MovementAdjustmentInput,
    MovementEntryInput,
    MovementExitInput,
)
from app.modules.inventory.application.service import MovementService
from app.modules.inventory.domain.enums import LocationType
from app.modules.inventory.domain.models import Location
from app.modules.transfers.application.schemas import (
    PhysicalCountCreateInput,
    PhysicalCountLineRecordInput,
    TransferCreateInput,
    TransferLineCreateInput,
)
from app.modules.transfers.application.service import PhysicalCountService, TransferService
from app.modules.transfers.domain.enums import PhysicalCountStatus, TransferStatus
from app.modules.transfers.domain.models import PhysicalCount, Transfer
from app.modules.purchasing.application.schemas import (
    POCreateInput,
    POLineCreateInput,
    ReceiptCreateInput,
    ReceiptLineCreateInput,
    InvoiceCreateInput,
)
from app.modules.purchasing.application.service import (
    PurchaseOrderService,
    ReceivingService,
    InvoiceService,
)
from app.modules.purchasing.domain.models import PurchaseOrder

configure_logging(json_logs=False, log_level="INFO")
log = structlog.get_logger()

TODAY = date.today()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

async def get_or_create(session: AsyncSession, model, unique_field: str, unique_value, **kwargs):
    """Fetch by unique_field; create with kwargs if absent. Returns (obj, created)."""
    stmt = select(model).where(
        getattr(model, unique_field) == unique_value,
        model.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is not None:
        return obj, False
    obj = model(**{unique_field: unique_value}, **kwargs)
    session.add(obj)
    await session.flush()
    return obj, True


async def get_or_create_link(
    session: AsyncSession,
    supplier_id,
    ingredient_id,
    supplier_sku: str | None,
    unit_cost: Decimal | None,
):
    stmt = select(SupplierIngredient).where(
        SupplierIngredient.supplier_id == supplier_id,
        SupplierIngredient.ingredient_id == ingredient_id,
        SupplierIngredient.is_deleted.is_(False),
    )
    result = await session.execute(stmt)
    obj = result.scalar_one_or_none()
    if obj is not None:
        return obj, False
    obj = SupplierIngredient(
        supplier_id=supplier_id,
        ingredient_id=ingredient_id,
        supplier_sku=supplier_sku,
        unit_cost=unit_cost,
    )
    session.add(obj)
    await session.flush()
    return obj, True


# ---------------------------------------------------------------------------
# catalog seed
# ---------------------------------------------------------------------------

async def seed_units(session: AsyncSession) -> dict[str, UnitOfMeasure]:
    """Returns a dict keyed by abbreviation."""
    units_data = [
        # weight
        dict(name="Kilogram",     abbreviation="kg",  unit_type=UnitType.weight, base_unit_id=None, conversion_factor=None),
        dict(name="Gram",         abbreviation="g",   unit_type=UnitType.weight, base_unit_id=None, conversion_factor=None),
        # volume
        dict(name="Litre",        abbreviation="L",   unit_type=UnitType.volume, base_unit_id=None, conversion_factor=None),
        dict(name="Millilitre",   abbreviation="mL",  unit_type=UnitType.volume, base_unit_id=None, conversion_factor=None),
        # unit
        dict(name="Unit",         abbreviation="u",   unit_type=UnitType.unit,   base_unit_id=None, conversion_factor=None),
        dict(name="Dozen",        abbreviation="doz", unit_type=UnitType.unit,   base_unit_id=None, conversion_factor=None),
        dict(name="Portion",      abbreviation="por", unit_type=UnitType.unit,   base_unit_id=None, conversion_factor=None),
    ]

    result: dict[str, UnitOfMeasure] = {}
    for data in units_data:
        abbr = data.pop("abbreviation")
        obj, created = await get_or_create(session, UnitOfMeasure, "abbreviation", abbr, **data)
        result[abbr] = obj
        if created:
            log.info("unit created", abbreviation=abbr)

    # Link derived units now that base units have IDs
    derivations = [
        ("g",   "kg",  Decimal("0.001")),
        ("mL",  "L",   Decimal("0.001")),
        ("doz", "u",   Decimal("12")),
    ]
    for derived_abbr, base_abbr, factor in derivations:
        derived = result[derived_abbr]
        if derived.base_unit_id is None:
            derived.base_unit_id = result[base_abbr].entity_id
            derived.conversion_factor = factor
            await session.flush()

    return result


async def seed_categories(session: AsyncSession) -> dict[str, Category]:
    """Returns a dict keyed by name."""
    top_level = [
        dict(name="Meats",      description="Fresh and frozen meat products"),
        dict(name="Vegetables", description="Fresh, frozen, and canned vegetables"),
        dict(name="Dairy",      description="Milk, cheese, butter, cream"),
        dict(name="Dry Goods",  description="Grains, flours, pasta, rice"),
        dict(name="Beverages",  description="Soft drinks, juices, water"),
        dict(name="Seafood",    description="Fresh and frozen seafood"),
        dict(name="Condiments", description="Sauces, oils, vinegars, spices"),
    ]

    result: dict[str, Category] = {}
    for data in top_level:
        name = data["name"]
        obj, created = await get_or_create(session, Category, "name", name, description=data["description"])
        result[name] = obj
        if created:
            log.info("category created", name=name)

    sub_categories = [
        ("Beef",        "Meats",      "Beef cuts and minced beef"),
        ("Poultry",     "Meats",      "Chicken, turkey, duck"),
        ("Pork",        "Meats",      "Pork cuts and charcuterie"),
        ("Leafy Greens","Vegetables", "Lettuce, spinach, arugula"),
        ("Root Vegetables","Vegetables","Carrots, potatoes, onions"),
        ("Cheese",      "Dairy",      "Soft and hard cheeses"),
        ("Oils & Fats", "Condiments", "Olive oil, butter, cooking oils"),
        ("Spices",      "Condiments", "Dried herbs and spices"),
    ]

    for name, parent_name, desc in sub_categories:
        obj, created = await get_or_create(
            session, Category, "name", name,
            description=desc,
            parent_id=result[parent_name].entity_id,
        )
        result[name] = obj
        if created:
            log.info("sub-category created", name=name, parent=parent_name)

    return result


async def seed_suppliers(session: AsyncSession) -> dict[str, Supplier]:
    suppliers_data = [
        dict(
            name="Fresh Farms Co.",
            contact_name="Maria González",
            email="orders@freshfarms.com",
            phone="+1-555-0101",
            address="12 Harvest Road, Springfield",
            tax_id="US-100001",
        ),
        dict(
            name="Prime Meats Ltd.",
            contact_name="Carlos Rodríguez",
            email="sales@primeats.com",
            phone="+1-555-0202",
            address="45 Butcher Lane, Meatville",
            tax_id="US-100002",
        ),
        dict(
            name="Ocean Catch Seafood",
            contact_name="Ana Martínez",
            email="fresh@oceancatch.com",
            phone="+1-555-0303",
            address="1 Harbor Quay, Port City",
            tax_id="US-100003",
        ),
        dict(
            name="Global Dry Goods Inc.",
            contact_name="James Lee",
            email="supply@globaldry.com",
            phone="+1-555-0404",
            address="78 Warehouse Blvd, Trade City",
            tax_id="US-100004",
        ),
    ]

    result: dict[str, Supplier] = {}
    for data in suppliers_data:
        name = data["name"]
        obj, created = await get_or_create(session, Supplier, "name", name, **{k: v for k, v in data.items() if k != "name"})
        result[name] = obj
        if created:
            log.info("supplier created", name=name)

    return result


async def seed_ingredients(
    session: AsyncSession,
    categories: dict[str, Category],
    units: dict[str, UnitOfMeasure],
    suppliers: dict[str, Supplier],
) -> dict[str, Ingredient]:
    """
    Each tuple: (sku, name, description, category_key, unit_abbr,
                 reorder_point, reorder_qty, cost_per_unit, allergen_info,
                 supplier_name, supplier_sku, supplier_cost)
    """
    ingredients_data = [
        # Beef
        ("BEEF-001", "Beef Tenderloin",    "Prime cut, 300-400g portions",     "Beef",           "kg",  "5",  "10",  "28.00", None,               "Prime Meats Ltd.", "BT-001", "25.00"),
        ("BEEF-002", "Ground Beef 80/20",  "Regular grind, 1 kg packs",        "Beef",           "kg",  "10", "20",  "8.50",  None,               "Prime Meats Ltd.", "GB-001", "7.80"),
        ("BEEF-003", "Beef Short Ribs",    "Bone-in, 500g portions",           "Beef",           "kg",  "4",  "8",   "14.00", None,               "Prime Meats Ltd.", "SR-001", "12.50"),
        # Poultry
        ("POL-001",  "Chicken Breast",     "Boneless, skinless",               "Poultry",        "kg",  "8",  "15",  "6.50",  None,               "Fresh Farms Co.", "CB-001", "5.90"),
        ("POL-002",  "Chicken Thigh",      "Bone-in, skin-on",                 "Poultry",        "kg",  "6",  "12",  "4.50",  None,               "Fresh Farms Co.", "CT-001", "4.00"),
        ("POL-003",  "Whole Duck",         "Approx. 2.5 kg each",              "Poultry",        "u",   "2",  "4",   "22.00", None,               "Prime Meats Ltd.", "WD-001", "20.00"),
        # Pork
        ("PORK-001", "Pork Belly",         "Skin-on, 1 kg slabs",              "Pork",           "kg",  "4",  "8",   "9.00",  None,               "Prime Meats Ltd.", "PB-001", "8.20"),
        ("PORK-002", "Bacon Strips",       "Smoked, 500g packs",               "Pork",           "kg",  "3",  "6",   "11.00", None,               "Prime Meats Ltd.", "BAC-001","10.00"),
        # Vegetables
        ("VEG-001",  "Tomato",             "Ripe Roma tomatoes",               "Root Vegetables","kg",  "5",  "20",  "1.50",  None,               "Fresh Farms Co.", "TOM-001","1.20"),
        ("VEG-002",  "Yellow Onion",       "Medium-sized",                     "Root Vegetables","kg",  "5",  "15",  "0.80",  None,               "Fresh Farms Co.", "ONI-001","0.70"),
        ("VEG-003",  "Carrot",             "Whole, unpeeled",                  "Root Vegetables","kg",  "4",  "10",  "0.90",  None,               "Fresh Farms Co.", "CAR-001","0.75"),
        ("VEG-004",  "Potato",             "Russet, 1 kg bag",                 "Root Vegetables","kg",  "8",  "25",  "0.70",  None,               "Fresh Farms Co.", "POT-001","0.60"),
        ("VEG-005",  "Garlic",             "Whole bulbs",                      "Root Vegetables","kg",  "2",  "5",   "4.00",  None,               "Fresh Farms Co.", "GAR-001","3.50"),
        ("VEG-006",  "Spinach",            "Baby spinach, washed",             "Leafy Greens",   "kg",  "2",  "4",   "3.50",  None,               "Fresh Farms Co.", "SPI-001","3.00"),
        ("VEG-007",  "Iceberg Lettuce",    "Whole head",                       "Leafy Greens",   "u",   "5",  "10",  "1.20",  None,               "Fresh Farms Co.", "LET-001","1.00"),
        ("VEG-008",  "Bell Pepper Red",    "Large, whole",                     "Root Vegetables","kg",  "3",  "8",   "2.80",  None,               "Fresh Farms Co.", "BPR-001","2.40"),
        # Dairy
        ("DAI-001",  "Whole Milk",         "Pasteurised, 1L carton",           "Dairy",          "L",   "10", "20",  "1.20",  "milk",             "Fresh Farms Co.", "MIL-001","1.00"),
        ("DAI-002",  "Heavy Cream",        "35% fat, 500mL",                   "Dairy",          "L",   "4",  "8",   "3.50",  "milk",             "Fresh Farms Co.", "CRE-001","3.00"),
        ("DAI-003",  "Butter Unsalted",    "250g blocks",                      "Dairy",          "kg",  "3",  "6",   "7.00",  "milk",             "Fresh Farms Co.", "BUT-001","6.20"),
        ("DAI-004",  "Parmesan Cheese",    "Aged, block",                      "Cheese",         "kg",  "1",  "2",   "22.00", "milk",             "Fresh Farms Co.", "PAR-001","20.00"),
        ("DAI-005",  "Mozzarella Fresh",   "125g balls in brine",              "Cheese",         "kg",  "2",  "4",   "12.00", "milk",             "Fresh Farms Co.", "MOZ-001","11.00"),
        # Dry goods
        ("DRY-001",  "All-Purpose Flour",  "Unbleached, 5 kg bag",             "Dry Goods",      "kg",  "10", "25",  "1.10",  "gluten",           "Global Dry Goods Inc.", "APF-001","0.95"),
        ("DRY-002",  "Arborio Rice",       "Short grain, 1 kg pack",           "Dry Goods",      "kg",  "4",  "10",  "2.80",  None,               "Global Dry Goods Inc.", "RIC-001","2.40"),
        ("DRY-003",  "Pasta Penne",        "500g pack, bronze die",            "Dry Goods",      "kg",  "4",  "10",  "2.20",  "gluten",           "Global Dry Goods Inc.", "PEN-001","1.90"),
        ("DRY-004",  "Breadcrumbs",        "Plain, fine",                      "Dry Goods",      "kg",  "3",  "6",   "1.80",  "gluten",           "Global Dry Goods Inc.", "BRC-001","1.50"),
        ("DRY-005",  "Olive Oil Extra V.", "Cold pressed, 1L bottle",          "Oils & Fats",    "L",   "3",  "6",   "8.50",  None,               "Global Dry Goods Inc.", "OLV-001","7.80"),
        ("DRY-006",  "Chicken Stock",      "1L carton, low sodium",            "Dry Goods",      "L",   "5",  "10",  "2.50",  None,               "Global Dry Goods Inc.", "CST-001","2.20"),
        # Spices
        ("SPC-001",  "Black Pepper Ground","100g tin",                         "Spices",         "g",   "50", "200", "0.04",  None,               "Global Dry Goods Inc.", "BPG-001","0.03"),
        ("SPC-002",  "Sea Salt Fine",      "1 kg bag",                         "Spices",         "kg",  "1",  "3",   "1.50",  None,               "Global Dry Goods Inc.", "SSL-001","1.20"),
        ("SPC-003",  "Paprika Smoked",     "75g tin",                          "Spices",         "g",   "30", "100", "0.05",  None,               "Global Dry Goods Inc.", "PAP-001","0.04"),
        ("SPC-004",  "Rosemary Dried",     "25g tin",                          "Spices",         "g",   "20", "80",  "0.08",  None,               "Global Dry Goods Inc.", "ROS-001","0.07"),
        # Seafood
        ("SEA-001",  "Atlantic Salmon",    "Fillet, skin-on, 200g portions",   "Seafood",        "kg",  "4",  "8",   "18.00", "fish",             "Ocean Catch Seafood", "SAL-001","16.50"),
        ("SEA-002",  "Tiger Prawns",       "16/20 count, IQF",                 "Seafood",        "kg",  "3",  "6",   "24.00", "shellfish",        "Ocean Catch Seafood", "PRW-001","22.00"),
        ("SEA-003",  "Tuna Loin",          "Sashimi grade",                    "Seafood",        "kg",  "2",  "4",   "32.00", "fish",             "Ocean Catch Seafood", "TUN-001","29.00"),
        # Beverages
        ("BEV-001",  "Sparkling Water",    "330mL cans, 24-pack",              "Beverages",      "u",   "24", "48",  "0.50",  None,               "Global Dry Goods Inc.", "SPW-001","0.40"),
        ("BEV-002",  "Orange Juice",       "100% pure, 1L carton",             "Beverages",      "L",   "4",  "10",  "2.20",  None,               "Fresh Farms Co.", "OJ-001", "1.90"),
    ]

    result: dict[str, Ingredient] = {}
    for row in ingredients_data:
        sku, name, desc, cat_key, unit_abbr, rp, rq, cpu, allergen, sup_name, sup_sku, sup_cost = row
        obj, created = await get_or_create(
            session, Ingredient, "sku", sku,
            name=name,
            description=desc,
            category_id=categories[cat_key].entity_id,
            unit_of_measure_id=units[unit_abbr].entity_id,
            reorder_point=Decimal(rp),
            reorder_quantity=Decimal(rq),
            cost_per_unit=Decimal(cpu),
            allergen_info=allergen,
            is_active=True,
        )
        result[sku] = obj
        if created:
            log.info("ingredient created", sku=sku, name=name)

        # supplier link
        _, link_created = await get_or_create_link(
            session,
            supplier_id=suppliers[sup_name].entity_id,
            ingredient_id=obj.entity_id,
            supplier_sku=sup_sku,
            unit_cost=Decimal(sup_cost),
        )
        if link_created:
            log.info("supplier link created", sku=sku, supplier=sup_name)

    return result


# ---------------------------------------------------------------------------
# inventory seed
# ---------------------------------------------------------------------------

async def seed_locations(session: AsyncSession) -> dict[str, Location]:
    locations_data = [
        dict(name="Main Warehouse",      code="WH-01", location_type=LocationType.warehouse, description="Primary dry goods and non-perishable storage"),
        dict(name="Walk-in Fridge",      code="FRG-01",location_type=LocationType.fridge,    description="Refrigerated storage 2–5°C"),
        dict(name="Walk-in Freezer",     code="FRZ-01",location_type=LocationType.freezer,   description="Deep freeze storage −18°C"),
        dict(name="Kitchen Prep Station",code="PROD-01",location_type=LocationType.production,description="Active kitchen prep area"),
        dict(name="Bar Storage",         code="BAR-01", location_type=LocationType.bar,       description="Bar spirits and beverage stock"),
    ]

    result: dict[str, Location] = {}
    for data in locations_data:
        code = data["code"]
        obj, created = await get_or_create(session, Location, "code", code, **{k: v for k, v in data.items() if k != "code"})
        result[code] = obj
        if created:
            log.info("location created", code=code, name=data["name"])

    return result


async def seed_inventory_movements(
    session: AsyncSession,
    ingredients: dict[str, Ingredient],
    locations: dict[str, Location],
) -> None:
    """
    Seed realistic stock movements for a typical week of restaurant operations.
    Only creates movements for ingredient+location pairs that have no kardex
    entries yet — fully idempotent.
    """
    from app.modules.inventory.infrastructure.repository import KardexRepository
    kardex_repo = KardexRepository(session)
    svc = MovementService(session)

    async def has_kardex(ingredient_id, location_id) -> bool:
        bal = await kardex_repo.get_last_balance(ingredient_id, location_id)
        return bal > Decimal("0")

    wh   = locations["WH-01"].entity_id
    frdg = locations["FRG-01"].entity_id
    frzr = locations["FRZ-01"].entity_id
    bar  = locations["BAR-01"].entity_id

    # ------------------------------------------------------------------
    # WAREHOUSE — dry goods, spices, beverages
    # ------------------------------------------------------------------
    warehouse_entries = [
        # (sku, qty, cost, batch, lot, received, expiry)
        ("DRY-001", "25.00",  "1.10",  "WH-APF-001", "L2025-07A", TODAY - timedelta(days=10), TODAY + timedelta(days=365)),
        ("DRY-002", "20.00",  "2.80",  "WH-RIC-001", "L2025-07B", TODAY - timedelta(days=10), None),
        ("DRY-003", "15.00",  "2.20",  "WH-PEN-001", "L2025-07C", TODAY - timedelta(days=10), TODAY + timedelta(days=180)),
        ("DRY-004", "8.00",   "1.80",  "WH-BRC-001", "L2025-07D", TODAY - timedelta(days=10), TODAY + timedelta(days=90)),
        ("DRY-005", "12.00",  "8.50",  "WH-OLV-001", "L2025-07E", TODAY - timedelta(days=10), TODAY + timedelta(days=540)),
        ("DRY-006", "20.00",  "2.50",  "WH-CST-001", "L2025-07F", TODAY - timedelta(days=10), TODAY + timedelta(days=60)),
        ("SPC-001", "500.00", "0.04",  "WH-BPG-001", "L2025-07G", TODAY - timedelta(days=15), TODAY + timedelta(days=730)),
        ("SPC-002", "10.00",  "1.50",  "WH-SSL-001", "L2025-07H", TODAY - timedelta(days=15), None),
        ("SPC-003", "300.00", "0.05",  "WH-PAP-001", "L2025-07I", TODAY - timedelta(days=15), TODAY + timedelta(days=730)),
        ("SPC-004", "200.00", "0.08",  "WH-ROS-001", "L2025-07J", TODAY - timedelta(days=15), TODAY + timedelta(days=730)),
        ("BEV-001", "96.00",  "0.50",  "WH-SPW-001", "L2025-07K", TODAY - timedelta(days=5),  TODAY + timedelta(days=360)),
    ]

    for sku, qty, cost, batch, lot, recv, exp in warehouse_entries:
        ing = ingredients[sku]
        if await has_kardex(ing.entity_id, wh):
            continue
        await svc.record_entry(MovementEntryInput(
            ingredient_id=ing.entity_id,
            location_id=wh,
            quantity=Decimal(qty),
            unit_cost=Decimal(cost),
            batch_number=batch,
            lot_number=lot,
            received_date=recv,
            expiry_date=exp,
        ))
        log.info("entry recorded", sku=sku, location="WH-01", qty=qty)

    # ------------------------------------------------------------------
    # FRIDGE — dairy, produce, beverages, fresh seafood
    # ------------------------------------------------------------------
    fridge_entries = [
        ("DAI-001", "30.00",  "1.20",  "FRG-MIL-001", "L2025-07A", TODAY - timedelta(days=3),  TODAY + timedelta(days=7)),
        ("DAI-002", "8.00",   "3.50",  "FRG-CRE-001", "L2025-07B", TODAY - timedelta(days=3),  TODAY + timedelta(days=5)),
        ("DAI-003", "5.00",   "7.00",  "FRG-BUT-001", "L2025-07C", TODAY - timedelta(days=3),  TODAY + timedelta(days=30)),
        ("DAI-004", "3.00",   "22.00", "FRG-PAR-001", "L2025-07D", TODAY - timedelta(days=5),  TODAY + timedelta(days=60)),
        ("DAI-005", "4.00",   "12.00", "FRG-MOZ-001", "L2025-07E", TODAY - timedelta(days=2),  TODAY + timedelta(days=5)),
        ("VEG-001", "15.00",  "1.50",  "FRG-TOM-001", "L2025-07F", TODAY - timedelta(days=2),  TODAY + timedelta(days=5)),
        ("VEG-002", "12.00",  "0.80",  "FRG-ONI-001", "L2025-07G", TODAY - timedelta(days=5),  TODAY + timedelta(days=14)),
        ("VEG-003", "10.00",  "0.90",  "FRG-CAR-001", "L2025-07H", TODAY - timedelta(days=5),  TODAY + timedelta(days=14)),
        ("VEG-004", "20.00",  "0.70",  "FRG-POT-001", "L2025-07I", TODAY - timedelta(days=7),  TODAY + timedelta(days=21)),
        ("VEG-005", "4.00",   "4.00",  "FRG-GAR-001", "L2025-07J", TODAY - timedelta(days=7),  TODAY + timedelta(days=30)),
        ("VEG-006", "5.00",   "3.50",  "FRG-SPI-001", "L2025-07K", TODAY - timedelta(days=1),  TODAY + timedelta(days=4)),
        ("VEG-007", "10.00",  "1.20",  "FRG-LET-001", "L2025-07L", TODAY - timedelta(days=1),  TODAY + timedelta(days=5)),
        ("VEG-008", "6.00",   "2.80",  "FRG-BPR-001", "L2025-07M", TODAY - timedelta(days=2),  TODAY + timedelta(days=7)),
        ("POL-001", "20.00",  "6.50",  "FRG-CB-001",  "L2025-07N", TODAY - timedelta(days=2),  TODAY + timedelta(days=3)),
        ("POL-002", "15.00",  "4.50",  "FRG-CT-001",  "L2025-07O", TODAY - timedelta(days=2),  TODAY + timedelta(days=3)),
        ("BEV-002", "12.00",  "2.20",  "FRG-OJ-001",  "L2025-07P", TODAY - timedelta(days=2),  TODAY + timedelta(days=7)),
        ("SEA-001", "8.00",   "18.00", "FRG-SAL-001", "L2025-07Q", TODAY - timedelta(days=1),  TODAY + timedelta(days=2)),
        ("SEA-002", "6.00",   "24.00", "FRG-PRW-001", "L2025-07R", TODAY - timedelta(days=1),  TODAY + timedelta(days=2)),
        ("SEA-003", "3.00",   "32.00", "FRG-TUN-001", "L2025-07S", TODAY,                       TODAY + timedelta(days=1)),
    ]

    for sku, qty, cost, batch, lot, recv, exp in fridge_entries:
        ing = ingredients[sku]
        if await has_kardex(ing.entity_id, frdg):
            continue
        await svc.record_entry(MovementEntryInput(
            ingredient_id=ing.entity_id,
            location_id=frdg,
            quantity=Decimal(qty),
            unit_cost=Decimal(cost),
            batch_number=batch,
            lot_number=lot,
            received_date=recv,
            expiry_date=exp,
        ))
        log.info("entry recorded", sku=sku, location="FRG-01", qty=qty)

    # ------------------------------------------------------------------
    # FREEZER — meats, frozen seafood, frozen poultry
    # ------------------------------------------------------------------
    freezer_entries = [
        ("BEEF-001", "15.00", "28.00", "FRZ-BT-001",  "L2025-07A", TODAY - timedelta(days=7),  TODAY + timedelta(days=180)),
        ("BEEF-002", "25.00", "8.50",  "FRZ-GB-001",  "L2025-07B", TODAY - timedelta(days=7),  TODAY + timedelta(days=180)),
        ("BEEF-003", "10.00", "14.00", "FRZ-SR-001",  "L2025-07C", TODAY - timedelta(days=7),  TODAY + timedelta(days=180)),
        ("PORK-001", "12.00", "9.00",  "FRZ-PB-001",  "L2025-07D", TODAY - timedelta(days=5),  TODAY + timedelta(days=120)),
        ("PORK-002", "8.00",  "11.00", "FRZ-BAC-001", "L2025-07E", TODAY - timedelta(days=5),  TODAY + timedelta(days=120)),
        ("POL-003",  "6.00",  "22.00", "FRZ-DUK-001", "L2025-07F", TODAY - timedelta(days=5),  TODAY + timedelta(days=120)),
        ("SEA-002",  "10.00", "24.00", "FRZ-PRW-001", "L2025-07G", TODAY - timedelta(days=10), TODAY + timedelta(days=365)),
    ]

    for sku, qty, cost, batch, lot, recv, exp in freezer_entries:
        ing = ingredients[sku]
        if await has_kardex(ing.entity_id, frzr):
            continue
        await svc.record_entry(MovementEntryInput(
            ingredient_id=ing.entity_id,
            location_id=frzr,
            quantity=Decimal(qty),
            unit_cost=Decimal(cost),
            batch_number=batch,
            lot_number=lot,
            received_date=recv,
            expiry_date=exp,
        ))
        log.info("entry recorded", sku=sku, location="FRZ-01", qty=qty)

    # ------------------------------------------------------------------
    # BAR — beverages
    # ------------------------------------------------------------------
    bar_entries = [
        ("BEV-001", "48.00", "0.50", "BAR-SPW-001", "L2025-07A", TODAY - timedelta(days=3), TODAY + timedelta(days=360)),
        ("BEV-002", "8.00",  "2.20", "BAR-OJ-001",  "L2025-07B", TODAY - timedelta(days=3), TODAY + timedelta(days=7)),
    ]

    for sku, qty, cost, batch, lot, recv, exp in bar_entries:
        ing = ingredients[sku]
        if await has_kardex(ing.entity_id, bar):
            continue
        await svc.record_entry(MovementEntryInput(
            ingredient_id=ing.entity_id,
            location_id=bar,
            quantity=Decimal(qty),
            unit_cost=Decimal(cost),
            batch_number=batch,
            lot_number=lot,
            received_date=recv,
            expiry_date=exp,
        ))
        log.info("entry recorded", sku=sku, location="BAR-01", qty=qty)

    # ------------------------------------------------------------------
    # Simulate daily kitchen consumption (exits from fridge)
    # ------------------------------------------------------------------
    daily_usage = [
        # (sku, qty, reason)
        ("POL-001", "4.00",  "Lunch and dinner service"),
        ("POL-002", "3.00",  "Lunch service"),
        ("VEG-001", "3.00",  "Sauce and garnish"),
        ("VEG-002", "2.00",  "Mise en place"),
        ("VEG-006", "1.00",  "Salad station"),
        ("DAI-003", "0.50",  "Sauce work"),
        ("DAI-001", "4.00",  "Baking and sauces"),
        ("SEA-001", "2.00",  "Dinner service"),
    ]

    for sku, qty, reason in daily_usage:
        ing = ingredients[sku]
        # only add exits if there was a fridge entry (balance > qty being exited)
        bal = await kardex_repo.get_last_balance(ing.entity_id, frdg)
        if bal <= Decimal("0"):
            continue
        # skip if we've already done this exit (balance < original entry)
        # Use a simple heuristic: if balance still equals entry quantity, create the exit
        entry_qty_map = {
            "POL-001": Decimal("20.00"), "POL-002": Decimal("15.00"),
            "VEG-001": Decimal("15.00"), "VEG-002": Decimal("12.00"),
            "VEG-006": Decimal("5.00"),  "DAI-003": Decimal("5.00"),
            "DAI-001": Decimal("30.00"), "SEA-001": Decimal("8.00"),
        }
        if bal < entry_qty_map.get(sku, Decimal("9999")):
            log.info("exit already applied, skipping", sku=sku)
            continue
        await svc.record_exit(MovementExitInput(
            ingredient_id=ing.entity_id,
            location_id=frdg,
            quantity=Decimal(qty),
            reason=reason,
            notes="Seeded daily kitchen consumption",
        ))
        log.info("exit recorded", sku=sku, location="FRG-01", qty=qty)

    # ------------------------------------------------------------------
    # One adjustment — spinach spoilage during fridge check
    # ------------------------------------------------------------------
    spinach = ingredients["VEG-006"]
    spinach_bal = await kardex_repo.get_last_balance(spinach.entity_id, frdg)
    # apply only if adjustment hasn't happened yet (balance still at post-exit level)
    post_exit_expected = Decimal("4.00")  # 5 entry − 1 exit
    if spinach_bal >= post_exit_expected:
        await svc.record_adjustment(MovementAdjustmentInput(
            ingredient_id=spinach.entity_id,
            location_id=frdg,
            quantity_delta=Decimal("-0.50"),
            reason="Spoilage found during morning fridge check",
            notes="Two bags partially wilted, discarded",
        ))
        log.info("adjustment recorded", sku="VEG-006", delta="-0.50")


# ---------------------------------------------------------------------------
# transfers seed
# ---------------------------------------------------------------------------

async def _transfer_exists(session: AsyncSession, transfer_number: str) -> bool:
    result = await session.execute(
        select(Transfer).where(
            Transfer.transfer_number == transfer_number,
            Transfer.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none() is not None


async def seed_transfers(
    session: AsyncSession,
    ingredients: dict[str, Ingredient],
    locations: dict[str, Location],
) -> None:
    """
    Seeds three realistic transfers that exercise the full lifecycle:

    1. WH-01 → FRG-01  (completed)  — daily fridge restock
    2. FRZ-01 → FRG-01 (in_transit) — frozen-to-fridge thawing transfer
    3. WH-01 → BAR-01  (draft)      — bar restock not yet sent
    """
    svc = TransferService(session)

    wh   = locations["WH-01"]
    frdg = locations["FRG-01"]
    frzr = locations["FRZ-01"]
    bar  = locations["BAR-01"]
    prod = locations["PROD-01"]

    from app.modules.transfers.infrastructure.repository import TransferRepository
    repo = TransferRepository(session)

    # ------------------------------------------------------------------
    # 1. Completed transfer: warehouse → bar (dry goods restock)
    #    WH-01 stocks: DRY-*, SPC-*, BEV-001
    # ------------------------------------------------------------------
    COMPLETED_NUM = "TRF-SEED-001"
    if not await _transfer_exists(session, COMPLETED_NUM):
        t1 = await svc.create(TransferCreateInput(
            from_location_id=wh.entity_id,
            to_location_id=bar.entity_id,
            notes="Bar restock — dry goods and beverages from warehouse",
        ))
        t1 = await repo.update(t1, transfer_number=COMPLETED_NUM)
        await session.commit()

        for sku, qty in [
            ("BEV-001", "12.00"),   # sparkling water — WH-01 has 96 units
            ("DRY-005", "2.00"),    # olive oil — WH-01 has 12 L
        ]:
            await svc.add_line(t1.entity_id, TransferLineCreateInput(
                ingredient_id=ingredients[sku].entity_id,
                requested_quantity=Decimal(qty),
            ))

        await svc.send(t1.entity_id)
        await svc.receive(t1.entity_id)
        log.info("transfer seeded (completed)", number=COMPLETED_NUM)
    else:
        log.info("transfer already exists, skipping", number=COMPLETED_NUM)

    # ------------------------------------------------------------------
    # 2. In-transit transfer: freezer → fridge (overnight thaw)
    #    FRZ-01 stocks: BEEF-001/002/003, PORK-001/002, POL-003, SEA-002
    # ------------------------------------------------------------------
    IN_TRANSIT_NUM = "TRF-SEED-002"
    if not await _transfer_exists(session, IN_TRANSIT_NUM):
        t2 = await svc.create(TransferCreateInput(
            from_location_id=frzr.entity_id,
            to_location_id=frdg.entity_id,
            notes="Overnight thaw — frozen meats to fridge for tomorrow's service",
        ))
        t2 = await repo.update(t2, transfer_number=IN_TRANSIT_NUM)
        await session.commit()

        for sku, qty in [
            ("BEEF-001", "3.00"),   # beef tenderloin — FRZ-01 has 15 kg
            ("PORK-001", "2.00"),   # pork belly — FRZ-01 has 12 kg
        ]:
            await svc.add_line(t2.entity_id, TransferLineCreateInput(
                ingredient_id=ingredients[sku].entity_id,
                requested_quantity=Decimal(qty),
            ))

        await svc.send(t2.entity_id)
        log.info("transfer seeded (in_transit)", number=IN_TRANSIT_NUM)
    else:
        log.info("transfer already exists, skipping", number=IN_TRANSIT_NUM)

    # ------------------------------------------------------------------
    # 3. Draft transfer: warehouse → kitchen (spice restocking, not yet sent)
    #    WH-01 stocks: SPC-001/002/003/004, DRY-*
    # ------------------------------------------------------------------
    DRAFT_NUM = "TRF-SEED-003"
    if not await _transfer_exists(session, DRAFT_NUM):
        t3 = await svc.create(TransferCreateInput(
            from_location_id=wh.entity_id,
            to_location_id=prod.entity_id,
            notes="Kitchen spice restocking — pending head chef approval",
        ))
        t3 = await repo.update(t3, transfer_number=DRAFT_NUM)
        await session.commit()

        for sku, qty in [
            ("SPC-001", "100.00"),  # black pepper — WH-01 has 500 g
            ("SPC-002", "2.00"),    # sea salt — WH-01 has 10 kg
            ("DRY-006", "5.00"),    # chicken stock — WH-01 has 20 L
        ]:
            await svc.add_line(t3.entity_id, TransferLineCreateInput(
                ingredient_id=ingredients[sku].entity_id,
                requested_quantity=Decimal(qty),
            ))

        log.info("transfer seeded (draft)", number=DRAFT_NUM)
    else:
        log.info("transfer already exists, skipping", number=DRAFT_NUM)


# ---------------------------------------------------------------------------
# physical counts seed
# ---------------------------------------------------------------------------

async def _count_exists(session: AsyncSession, location_id, notes_prefix: str) -> bool:
    result = await session.execute(
        select(PhysicalCount).where(
            PhysicalCount.location_id == location_id,
            PhysicalCount.notes.like(f"{notes_prefix}%"),
            PhysicalCount.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none() is not None


async def seed_physical_counts(
    session: AsyncSession,
    locations: dict[str, Location],
) -> None:
    """
    Seeds two physical counts:

    1. Walk-in Fridge — completed, with realistic variances applied
    2. Main Warehouse  — in_progress, partially counted (some lines still null)
    """
    svc = PhysicalCountService(session)

    frdg = locations["FRG-01"]
    wh   = locations["WH-01"]

    # ------------------------------------------------------------------
    # 1. Completed count: fridge — weekly check found minor shrinkage
    # ------------------------------------------------------------------
    FRIDGE_NOTES = "[SEED] Weekly fridge count — post-service"
    if not await _count_exists(session, frdg.entity_id, "[SEED] Weekly fridge"):
        count1 = await svc.create(PhysicalCountCreateInput(
            location_id=frdg.entity_id,
            notes=FRIDGE_NOTES,
        ))

        lines = await svc.list_lines(count1.entity_id)

        # Submit counted quantities — most match system, a few have variance
        variances: dict[str, Decimal] = {
            # sku-like hint: we identify lines by ingredient_id later
            # negative = found less than system (shrinkage/spillage)
            # positive = found more (unrecorded entry)
        }

        # Build ingredient_id → adjustment map from the seeded ingredients
        # We use the known seeded stock levels and apply small realistic variances
        # keyed by ingredient position in the lines list
        for i, line in enumerate(lines):
            if i % 4 == 0:
                # Every 4th line: slight deficit (spillage, evaporation)
                counted = max(Decimal("0"), line.system_quantity - Decimal("0.30"))
            elif i % 7 == 0:
                # Every 7th line: slight surplus (unregistered delivery fragment)
                counted = line.system_quantity + Decimal("0.20")
            else:
                # All others: exact match
                counted = line.system_quantity

            await svc.record_line(
                count1.entity_id,
                line.entity_id,
                PhysicalCountLineRecordInput(counted_quantity=counted),
            )

        await svc.complete(count1.entity_id)
        log.info("physical count seeded (completed)", location="FRG-01")
    else:
        log.info("physical count already exists, skipping", location="FRG-01")

    # ------------------------------------------------------------------
    # 2. In-progress count: warehouse — partially counted
    # ------------------------------------------------------------------
    WH_NOTES = "[SEED] Monthly warehouse stocktake — in progress"
    if not await _count_exists(session, wh.entity_id, "[SEED] Monthly warehouse"):
        count2 = await svc.create(PhysicalCountCreateInput(
            location_id=wh.entity_id,
            notes=WH_NOTES,
        ))

        lines = await svc.list_lines(count2.entity_id)

        # Only count the first half of lines — simulates staff still working
        halfway = len(lines) // 2
        for line in lines[:halfway]:
            counted = max(Decimal("0"), line.system_quantity - Decimal("0.10"))
            await svc.record_line(
                count2.entity_id,
                line.entity_id,
                PhysicalCountLineRecordInput(counted_quantity=counted),
            )

        # Leave the rest as null — count is still in_progress
        log.info(
            "physical count seeded (in_progress)",
            location="WH-01",
            lines_counted=halfway,
            lines_pending=len(lines) - halfway,
        )
    else:
        log.info("physical count already exists, skipping", location="WH-01")


# ---------------------------------------------------------------------------
# purchasing seed
# ---------------------------------------------------------------------------

async def _po_exists(session: AsyncSession, po_number: str) -> bool:
    result = await session.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.po_number == po_number,
            PurchaseOrder.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none() is not None


async def seed_purchasing(
    session: AsyncSession,
    ingredients: dict[str, object],
    locations: dict[str, object],
    suppliers: dict[str, object],
) -> None:
    """
    Seeds three purchase orders covering the main PO lifecycle states:

    PO-SEED-001  — Prime Meats Ltd.   — fully received + matched invoice
    PO-SEED-002  — Global Dry Goods   — sent, partially received (one receipt completed)
    PO-SEED-003  — Fresh Farms Co.    — draft (not yet sent)
    """
    po_svc = PurchaseOrderService(session)
    rcv_svc = ReceivingService(session)
    inv_svc = InvoiceService(session)

    # -----------------------------------------------------------------------
    # PO-SEED-001: Prime Meats Ltd. — fully received, invoice matched
    # -----------------------------------------------------------------------
    MEATS_PO_NUMBER = "PO-SEED-001"
    if not await _po_exists(session, MEATS_PO_NUMBER):
        po1 = await po_svc.create(
            POCreateInput(
                supplier_id=suppliers["Prime Meats Ltd."].entity_id,
                expected_delivery_date=TODAY - timedelta(days=3),
                notes="[SEED] Weekly meat restocking order",
            )
        )
        # Override auto-generated number with stable seed key
        po1_repo = po_svc.repo
        po1 = await po1_repo.update(po1, po_number=MEATS_PO_NUMBER)
        await session.commit()

        # Add lines
        beef_line = await po_svc.add_line(
            po1.entity_id,
            POLineCreateInput(
                ingredient_id=ingredients["BEEF-001"].entity_id,
                ordered_quantity=Decimal("15.00"),
                unit_cost=Decimal("25.00"),
            ),
        )
        await po_svc.add_line(
            po1.entity_id,
            POLineCreateInput(
                ingredient_id=ingredients["PORK-001"].entity_id,
                ordered_quantity=Decimal("10.00"),
                unit_cost=Decimal("8.20"),
            ),
        )
        await po_svc.add_line(
            po1.entity_id,
            POLineCreateInput(
                ingredient_id=ingredients["BEEF-002"].entity_id,
                ordered_quantity=Decimal("20.00"),
                unit_cost=Decimal("7.80"),
            ),
        )

        # Send
        po1 = await po_svc.send(po1.entity_id)

        # Create and complete a goods receipt
        receipt1 = await rcv_svc.create(
            ReceiptCreateInput(
                order_id=po1.entity_id,
                destination_location_id=locations["FRZ-01"].entity_id,
                notes="[SEED] Meat delivery received at freezer",
            )
        )
        await rcv_svc.add_line(
            receipt1.entity_id,
            ReceiptLineCreateInput(
                ingredient_id=ingredients["BEEF-001"].entity_id,
                batch_number="PO-SEED-001-BEEF-001",
                lot_number="L2025-MEATS-A",
                expiry_date=TODAY + timedelta(days=14),
                received_quantity=Decimal("15.00"),
                unit_cost=Decimal("25.00"),
            ),
        )
        await rcv_svc.add_line(
            receipt1.entity_id,
            ReceiptLineCreateInput(
                ingredient_id=ingredients["PORK-001"].entity_id,
                batch_number="PO-SEED-001-PORK-001",
                lot_number="L2025-MEATS-B",
                expiry_date=TODAY + timedelta(days=10),
                received_quantity=Decimal("10.00"),
                unit_cost=Decimal("8.20"),
            ),
        )
        await rcv_svc.add_line(
            receipt1.entity_id,
            ReceiptLineCreateInput(
                ingredient_id=ingredients["BEEF-002"].entity_id,
                batch_number="PO-SEED-001-BEEF-002",
                lot_number="L2025-MEATS-C",
                expiry_date=TODAY + timedelta(days=12),
                received_quantity=Decimal("20.00"),
                unit_cost=Decimal("7.80"),
            ),
        )
        await rcv_svc.complete(receipt1.entity_id)

        # Create invoice and match it
        invoice1 = await inv_svc.create(
            InvoiceCreateInput(
                order_id=po1.entity_id,
                invoice_number="INV-MEATS-SEED-001",
                invoice_date=TODAY - timedelta(days=3),
                due_date=TODAY + timedelta(days=27),
                total_amount=Decimal("15.00") * Decimal("25.00")
                    + Decimal("10.00") * Decimal("8.20")
                    + Decimal("20.00") * Decimal("7.80"),
                notes="[SEED] Invoice from Prime Meats",
            )
        )
        await inv_svc.match(invoice1.entity_id)

        log.info(
            "PO seeded (fully received, invoice matched)",
            po_number=MEATS_PO_NUMBER,
            supplier="Prime Meats Ltd.",
        )
    else:
        log.info("PO already exists, skipping", po_number=MEATS_PO_NUMBER)

    # -----------------------------------------------------------------------
    # PO-SEED-002: Global Dry Goods — sent, partially received
    # -----------------------------------------------------------------------
    DRY_PO_NUMBER = "PO-SEED-002"
    if not await _po_exists(session, DRY_PO_NUMBER):
        po2 = await po_svc.create(
            POCreateInput(
                supplier_id=suppliers["Global Dry Goods Inc."].entity_id,
                expected_delivery_date=TODAY + timedelta(days=2),
                notes="[SEED] Dry goods replenishment order",
            )
        )
        po2_repo = po_svc.repo
        po2 = await po2_repo.update(po2, po_number=DRY_PO_NUMBER)
        await session.commit()

        await po_svc.add_line(
            po2.entity_id,
            POLineCreateInput(
                ingredient_id=ingredients["DRY-001"].entity_id,
                ordered_quantity=Decimal("50.00"),
                unit_cost=Decimal("0.95"),
            ),
        )
        await po_svc.add_line(
            po2.entity_id,
            POLineCreateInput(
                ingredient_id=ingredients["DRY-005"].entity_id,
                ordered_quantity=Decimal("24.00"),
                unit_cost=Decimal("7.80"),
            ),
        )
        await po_svc.add_line(
            po2.entity_id,
            POLineCreateInput(
                ingredient_id=ingredients["SPC-001"].entity_id,
                ordered_quantity=Decimal("1000.00"),
                unit_cost=Decimal("0.03"),
            ),
        )

        po2 = await po_svc.send(po2.entity_id)

        # Partial receipt — only DRY-001 and DRY-005 delivered so far
        receipt2 = await rcv_svc.create(
            ReceiptCreateInput(
                order_id=po2.entity_id,
                destination_location_id=locations["WH-01"].entity_id,
                notes="[SEED] Partial dry goods delivery",
            )
        )
        await rcv_svc.add_line(
            receipt2.entity_id,
            ReceiptLineCreateInput(
                ingredient_id=ingredients["DRY-001"].entity_id,
                batch_number="PO-SEED-002-DRY-001",
                lot_number="L2025-DRY-A",
                expiry_date=TODAY + timedelta(days=365),
                received_quantity=Decimal("50.00"),
                unit_cost=Decimal("0.95"),
            ),
        )
        await rcv_svc.add_line(
            receipt2.entity_id,
            ReceiptLineCreateInput(
                ingredient_id=ingredients["DRY-005"].entity_id,
                batch_number="PO-SEED-002-DRY-005",
                lot_number="L2025-DRY-B",
                expiry_date=TODAY + timedelta(days=540),
                received_quantity=Decimal("24.00"),
                unit_cost=Decimal("7.80"),
            ),
        )
        await rcv_svc.complete(receipt2.entity_id)

        # Invoice pending for partial amount
        await inv_svc.create(
            InvoiceCreateInput(
                order_id=po2.entity_id,
                invoice_number="INV-DRY-SEED-001",
                invoice_date=TODAY,
                due_date=TODAY + timedelta(days=30),
                total_amount=Decimal("50.00") * Decimal("0.95")
                    + Decimal("24.00") * Decimal("7.80"),
                notes="[SEED] Partial invoice — SPC-001 pending",
            )
        )

        log.info(
            "PO seeded (partially received, invoice pending)",
            po_number=DRY_PO_NUMBER,
            supplier="Global Dry Goods Inc.",
        )
    else:
        log.info("PO already exists, skipping", po_number=DRY_PO_NUMBER)

    # -----------------------------------------------------------------------
    # PO-SEED-003: Fresh Farms Co. — draft (not yet sent)
    # -----------------------------------------------------------------------
    FARMS_PO_NUMBER = "PO-SEED-003"
    if not await _po_exists(session, FARMS_PO_NUMBER):
        po3 = await po_svc.create(
            POCreateInput(
                supplier_id=suppliers["Fresh Farms Co."].entity_id,
                expected_delivery_date=TODAY + timedelta(days=5),
                notes="[SEED] Vegetables and dairy restock",
            )
        )
        po3_repo = po_svc.repo
        po3 = await po3_repo.update(po3, po_number=FARMS_PO_NUMBER)
        await session.commit()

        await po_svc.add_line(
            po3.entity_id,
            POLineCreateInput(
                ingredient_id=ingredients["VEG-001"].entity_id,
                ordered_quantity=Decimal("20.00"),
                unit_cost=Decimal("1.20"),
            ),
        )
        await po_svc.add_line(
            po3.entity_id,
            POLineCreateInput(
                ingredient_id=ingredients["VEG-004"].entity_id,
                ordered_quantity=Decimal("30.00"),
                unit_cost=Decimal("0.60"),
            ),
        )
        await po_svc.add_line(
            po3.entity_id,
            POLineCreateInput(
                ingredient_id=ingredients["DAI-001"].entity_id,
                ordered_quantity=Decimal("40.00"),
                unit_cost=Decimal("1.00"),
            ),
        )
        await po_svc.add_line(
            po3.entity_id,
            POLineCreateInput(
                ingredient_id=ingredients["DAI-003"].entity_id,
                ordered_quantity=Decimal("8.00"),
                unit_cost=Decimal("6.20"),
            ),
        )

        log.info(
            "PO seeded (draft, not yet sent)",
            po_number=FARMS_PO_NUMBER,
            supplier="Fresh Farms Co.",
        )
    else:
        log.info("PO already exists, skipping", po_number=FARMS_PO_NUMBER)


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------

async def run_seed() -> None:
    log.info("seed started", database=settings.database_url.split("@")[-1])

    async with async_session_factory() as session:
        async with session.begin():
            # Catalog
            log.info("--- seeding catalog ---")
            units      = await seed_units(session)
            categories = await seed_categories(session)
            suppliers  = await seed_suppliers(session)
            ingredients = await seed_ingredients(session, categories, units, suppliers)

            # Inventory
            log.info("--- seeding inventory locations ---")
            locations  = await seed_locations(session)

        # Movements need their own commits (MovementService commits internally)
        log.info("--- seeding inventory movements ---")
        await seed_inventory_movements(session, ingredients, locations)

        # Transfers (TransferService commits internally)
        log.info("--- seeding transfers ---")
        await seed_transfers(session, ingredients, locations)

        # Physical counts (PhysicalCountService commits internally)
        log.info("--- seeding physical counts ---")
        await seed_physical_counts(session, locations)

        # Purchasing (PurchaseOrderService, ReceivingService, InvoiceService commit internally)
        log.info("--- seeding purchasing ---")
        await seed_purchasing(session, ingredients, locations, suppliers)

    log.info("seed complete")


if __name__ == "__main__":
    asyncio.run(run_seed())
