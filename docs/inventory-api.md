# Inventory API Reference

Base URL: `http://localhost:8000/api/v1/inventory`

---

## Response Envelope

All endpoints wrap their payload in a consistent envelope.

**Success**
```json
{
  "data": { ... }
}
```

**Error**
```json
{
  "message": "Human-readable description",
  "errors": [
    { "field": "quantity", "message": "Input should be greater than 0" }
  ]
}
```

**Paginated list**
```json
{
  "data": {
    "items": [ ... ],
    "total": 42,
    "page": 1,
    "size": 20,
    "pages": 3
  }
}
```

---

## Locations

Storage locations where stock is held (warehouse, fridge, freezer, bar, production).

### GET /api/v1/inventory/locations/select

Returns a lightweight list of active locations for dropdown use.

```bash
curl http://localhost:8000/api/v1/inventory/locations/select
```

**Response 200**
```json
{
  "data": [
    {
      "entity_id": "11111111-0000-0000-0000-000000000001",
      "name": "Main Warehouse",
      "code": "WH-01"
    }
  ]
}
```

---

### GET /api/v1/inventory/locations/

**Query parameters**

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| `page` | int | — | Page number (default 1) |
| `size` | int | — | Page size (default 20) |
| `location_type` | string | `warehouse`, `fridge`, `freezer`, `bar`, `production` | Filter by type |
| `is_active` | bool | — | Filter by active status |

```bash
# All active fridges
curl "http://localhost:8000/api/v1/inventory/locations/?location_type=fridge&is_active=true"
```

**Response 200**
```json
{
  "data": {
    "items": [
      {
        "entity_id": "11111111-0000-0000-0000-000000000001",
        "name": "Main Warehouse",
        "code": "WH-01",
        "location_type": "warehouse",
        "description": "Primary dry goods storage",
        "is_active": true,
        "created_at": "2025-07-25T10:00:00Z",
        "updated_at": "2025-07-25T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "size": 20,
    "pages": 1
  }
}
```

---

### POST /api/v1/inventory/locations/

**Full body**
```json
{
  "name": "Main Warehouse",
  "code": "WH-01",
  "location_type": "warehouse",
  "description": "Primary dry goods storage",
  "is_active": true
}
```

**Minimal body**
```json
{
  "name": "Main Warehouse",
  "code": "WH-01",
  "location_type": "warehouse"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/inventory/locations/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Main Warehouse", "code": "WH-01", "location_type": "warehouse"}'
```

**Response 201**
```json
{
  "data": {
    "entity_id": "11111111-0000-0000-0000-000000000001",
    "name": "Main Warehouse",
    "code": "WH-01",
    "location_type": "warehouse",
    "description": null,
    "is_active": true,
    "created_at": "2025-07-25T10:00:00Z",
    "updated_at": "2025-07-25T10:00:00Z"
  }
}
```

**Error 409 — duplicate code**
```json
{
  "message": "Location with code 'WH-01' already exists",
  "errors": []
}
```

---

### GET /api/v1/inventory/locations/{location_id}

```bash
curl http://localhost:8000/api/v1/inventory/locations/11111111-0000-0000-0000-000000000001
```

**Response 200** — same shape as the item in the list response.

**Error 404**
```json
{
  "message": "Location not found",
  "errors": []
}
```

---

### PATCH /api/v1/inventory/locations/{location_id}

All fields optional.

**Body**
```json
{
  "name": "Main Warehouse (Dry)",
  "description": "Dry goods and non-perishables"
}
```

```bash
curl -X PATCH http://localhost:8000/api/v1/inventory/locations/11111111-0000-0000-0000-000000000001 \
  -H "Content-Type: application/json" \
  -d '{"description": "Dry goods and non-perishables"}'
```

**Response 200** — updated location object.

---

### DELETE /api/v1/inventory/locations/{location_id}

Soft-deletes the location. Rejects if the location still has stock items.

```bash
curl -X DELETE http://localhost:8000/api/v1/inventory/locations/11111111-0000-0000-0000-000000000001
```

**Response 204** — no body.

**Error 400 — location in use**
```json
{
  "message": "Cannot delete location with stock items",
  "errors": []
}
```

---

### PATCH /api/v1/inventory/locations/{location_id}/activate

```bash
curl -X PATCH http://localhost:8000/api/v1/inventory/locations/11111111-0000-0000-0000-000000000001/activate
```

**Response 200** — location object with `"is_active": true`.

---

### PATCH /api/v1/inventory/locations/{location_id}/deactivate

```bash
curl -X PATCH http://localhost:8000/api/v1/inventory/locations/11111111-0000-0000-0000-000000000001/deactivate
```

**Response 200** — location object with `"is_active": false`.

---

## Stock

Current stock levels per ingredient per location. Read-only — stock is modified exclusively through movements.

### GET /api/v1/inventory/stock/

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `size` | int | Page size |
| `ingredient_id` | UUID | Filter by ingredient |
| `location_id` | UUID | Filter by location |

```bash
# All stock at a specific location
curl "http://localhost:8000/api/v1/inventory/stock/?location_id=11111111-0000-0000-0000-000000000001"

# All locations where a specific ingredient is stocked
curl "http://localhost:8000/api/v1/inventory/stock/?ingredient_id=a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
```

**Response 200**
```json
{
  "data": {
    "items": [
      {
        "entity_id": "22222222-0000-0000-0000-000000000001",
        "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "location_id": "11111111-0000-0000-0000-000000000001",
        "quantity_on_hand": "50.0000",
        "quantity_reserved": "5.0000",
        "quantity_available": "45.0000",
        "created_at": "2025-07-25T10:00:00Z",
        "updated_at": "2025-07-25T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "size": 20,
    "pages": 1
  }
}
```

> `quantity_available = quantity_on_hand - quantity_reserved`

---

### GET /api/v1/inventory/stock/low-stock

Returns all stock items where `quantity_on_hand <= ingredient.reorder_point`.

```bash
curl http://localhost:8000/api/v1/inventory/stock/low-stock
```

**Response 200**
```json
{
  "data": [
    {
      "entity_id": "22222222-0000-0000-0000-000000000002",
      "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "location_id": "11111111-0000-0000-0000-000000000001",
      "quantity_on_hand": "3.0000",
      "quantity_reserved": "0.0000",
      "quantity_available": "3.0000",
      "created_at": "2025-07-25T10:00:00Z",
      "updated_at": "2025-07-25T10:00:00Z"
    }
  ]
}
```

---

### GET /api/v1/inventory/stock/{ingredient_id}/locations

All stock entries across every location for one ingredient.

```bash
curl http://localhost:8000/api/v1/inventory/stock/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11/locations
```

**Response 200**
```json
{
  "data": [
    {
      "entity_id": "22222222-0000-0000-0000-000000000001",
      "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "location_id": "11111111-0000-0000-0000-000000000001",
      "quantity_on_hand": "50.0000",
      "quantity_reserved": "0.0000",
      "quantity_available": "50.0000",
      "created_at": "2025-07-25T10:00:00Z",
      "updated_at": "2025-07-25T10:00:00Z"
    },
    {
      "entity_id": "22222222-0000-0000-0000-000000000003",
      "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "location_id": "11111111-0000-0000-0000-000000000002",
      "quantity_on_hand": "12.0000",
      "quantity_reserved": "0.0000",
      "quantity_available": "12.0000",
      "created_at": "2025-07-25T10:00:00Z",
      "updated_at": "2025-07-25T10:00:00Z"
    }
  ]
}
```

---

## Movements

The only way to change stock levels. Every movement creates a `StockMovement` record and appends a `KardexEntry`.

### Movement types

| Type | Direction | Triggered by |
|------|-----------|--------------|
| `entry` | +stock | Receiving goods, manual entry |
| `exit` | -stock | Manual exit |
| `adjustment` | ±stock | Physical count correction |
| `transfer_out` | -stock | Inter-location transfer (future) |
| `transfer_in` | +stock | Inter-location transfer (future) |
| `waste` | -stock | Waste module |
| `production_consumption` | -stock | Production module |
| `sales_deduction` | -stock | Sales module |
| `physical_count` | ±stock | Physical count reconciliation |

---

### POST /api/v1/inventory/movements/entry

Records a stock entry. Creates a batch, upserts the stock item, and appends a kardex entry — all in one transaction.

**Full body**
```json
{
  "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "location_id": "11111111-0000-0000-0000-000000000001",
  "quantity": "50.00",
  "unit_cost": "1.50",
  "batch_number": "BATCH-2025-001",
  "lot_number": "LOT-A",
  "expiry_date": "2025-12-31",
  "received_date": "2025-07-25",
  "supplier_id": "b5c6d7e8-5717-4562-b3fc-2c963f66afa6",
  "reference_type": "purchase_order",
  "reference_id": "ffffffff-0000-0000-0000-000000000001",
  "notes": "First delivery from supplier"
}
```

**Minimal body**
```json
{
  "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "location_id": "11111111-0000-0000-0000-000000000001",
  "quantity": "50.00",
  "unit_cost": "1.50",
  "batch_number": "BATCH-2025-001",
  "received_date": "2025-07-25"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/inventory/movements/entry \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "location_id": "11111111-0000-0000-0000-000000000001",
    "quantity": "50.00",
    "unit_cost": "1.50",
    "batch_number": "BATCH-2025-001",
    "received_date": "2025-07-25"
  }'
```

**Response 201**
```json
{
  "data": {
    "entity_id": "33333333-0000-0000-0000-000000000001",
    "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "location_id": "11111111-0000-0000-0000-000000000001",
    "batch_id": "44444444-0000-0000-0000-000000000001",
    "movement_type": "entry",
    "quantity": "50.0000",
    "unit_cost": "1.5000",
    "reference_type": null,
    "reference_id": null,
    "reason": null,
    "notes": null,
    "performed_by": null,
    "created_at": "2025-07-25T10:00:00Z",
    "updated_at": "2025-07-25T10:00:00Z"
  }
}
```

**Error 404 — ingredient or location not found**
```json
{
  "message": "Ingredient not found",
  "errors": []
}
```

---

### POST /api/v1/inventory/movements/exit

Records a stock exit using **FIFO batch deduction** (oldest `received_date` first, then earliest `expiry_date`).

**Full body**
```json
{
  "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "location_id": "11111111-0000-0000-0000-000000000001",
  "quantity": "10.00",
  "reference_type": "sales_order",
  "reference_id": "ffffffff-0000-0000-0000-000000000002",
  "reason": "Kitchen request",
  "notes": "Used for lunch service"
}
```

**Minimal body**
```json
{
  "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "location_id": "11111111-0000-0000-0000-000000000001",
  "quantity": "10.00"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/inventory/movements/exit \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "location_id": "11111111-0000-0000-0000-000000000001",
    "quantity": "10.00"
  }'
```

**Response 201** — same shape as entry response, with `"movement_type": "exit"`.

**Error 400 — insufficient stock**
```json
{
  "message": "Insufficient stock: available=5.0000, requested=10.0000",
  "errors": []
}
```

**Error 404 — no stock at location**
```json
{
  "message": "No stock found for this ingredient at this location",
  "errors": []
}
```

---

### POST /api/v1/inventory/movements/adjustment

Records a stock adjustment. `quantity_delta` can be positive (add stock) or negative (remove stock).

**Full body**
```json
{
  "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "location_id": "11111111-0000-0000-0000-000000000001",
  "quantity_delta": "-3.50",
  "reason": "Physical count variance — actual lower than system",
  "notes": "Counted 46.5 kg, system showed 50 kg",
  "unit_cost": "1.50"
}
```

**Minimal body** (`unit_cost` defaults to the last recorded unit cost from kardex)
```json
{
  "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "location_id": "11111111-0000-0000-0000-000000000001",
  "quantity_delta": "5.00",
  "reason": "Found unlisted stock during stocktake"
}
```

```bash
# Negative adjustment (reduce stock)
curl -X POST http://localhost:8000/api/v1/inventory/movements/adjustment \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "location_id": "11111111-0000-0000-0000-000000000001",
    "quantity_delta": "-3.50",
    "reason": "Physical count variance"
  }'

# Positive adjustment (add stock)
curl -X POST http://localhost:8000/api/v1/inventory/movements/adjustment \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "location_id": "11111111-0000-0000-0000-000000000001",
    "quantity_delta": "5.00",
    "reason": "Found unlisted stock during stocktake"
  }'
```

**Response 201** — same shape as entry/exit response, with `"movement_type": "adjustment"`.

**Error 400 — would result in negative stock**
```json
{
  "message": "Adjustment would result in negative stock",
  "errors": []
}
```

---

### GET /api/v1/inventory/movements/

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `size` | int | Page size |
| `ingredient_id` | UUID | Filter by ingredient |
| `location_id` | UUID | Filter by location |
| `movement_type` | string | Filter by type (see table above) |
| `reference_type` | string | Filter by reference type (e.g. `purchase_order`) |

```bash
# All exits for a specific ingredient
curl "http://localhost:8000/api/v1/inventory/movements/?ingredient_id=a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11&movement_type=exit"

# All movements linked to purchase orders
curl "http://localhost:8000/api/v1/inventory/movements/?reference_type=purchase_order"
```

**Response 200**
```json
{
  "data": {
    "items": [
      {
        "entity_id": "33333333-0000-0000-0000-000000000001",
        "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "location_id": "11111111-0000-0000-0000-000000000001",
        "batch_id": "44444444-0000-0000-0000-000000000001",
        "movement_type": "entry",
        "quantity": "50.0000",
        "unit_cost": "1.5000",
        "reference_type": null,
        "reference_id": null,
        "reason": null,
        "notes": null,
        "performed_by": null,
        "created_at": "2025-07-25T10:00:00Z",
        "updated_at": "2025-07-25T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "size": 20,
    "pages": 1
  }
}
```

---

## Batches

Lot/batch records created automatically on every `entry` movement.

### GET /api/v1/inventory/batches/

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `size` | int | Page size |
| `ingredient_id` | UUID | Filter by ingredient |
| `location_id` | UUID | Filter by location |
| `supplier_id` | UUID | Filter by supplier |

```bash
curl "http://localhost:8000/api/v1/inventory/batches/?ingredient_id=a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
```

**Response 200**
```json
{
  "data": {
    "items": [
      {
        "entity_id": "44444444-0000-0000-0000-000000000001",
        "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "location_id": "11111111-0000-0000-0000-000000000001",
        "batch_number": "BATCH-2025-001",
        "lot_number": "LOT-A",
        "quantity": "40.0000",
        "expiry_date": "2025-12-31",
        "received_date": "2025-07-25",
        "unit_cost": "1.5000",
        "supplier_id": "b5c6d7e8-5717-4562-b3fc-2c963f66afa6",
        "created_at": "2025-07-25T10:00:00Z",
        "updated_at": "2025-07-25T10:00:00Z"
      }
    ],
    "total": 1,
    "page": 1,
    "size": 20,
    "pages": 1
  }
}
```

> `quantity` reflects remaining stock — it decreases as FIFO exit movements consume the batch.

---

### GET /api/v1/inventory/batches/expiring-soon

Returns batches expiring within the next N days with remaining quantity > 0.

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 7 | Look-ahead window (1–365) |

```bash
# Expiring in the next 3 days
curl "http://localhost:8000/api/v1/inventory/batches/expiring-soon?days=3"

# Expiring in the next 30 days
curl "http://localhost:8000/api/v1/inventory/batches/expiring-soon?days=30"
```

**Response 200**
```json
{
  "data": [
    {
      "entity_id": "44444444-0000-0000-0000-000000000002",
      "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "location_id": "11111111-0000-0000-0000-000000000001",
      "batch_number": "BATCH-2025-002",
      "lot_number": null,
      "quantity": "8.0000",
      "expiry_date": "2025-07-27",
      "received_date": "2025-07-10",
      "unit_cost": "1.50",
      "supplier_id": null,
      "created_at": "2025-07-10T09:00:00Z",
      "updated_at": "2025-07-10T09:00:00Z"
    }
  ]
}
```

---

### GET /api/v1/inventory/batches/{batch_id}

```bash
curl http://localhost:8000/api/v1/inventory/batches/44444444-0000-0000-0000-000000000001
```

**Response 200** — same shape as the item in the list response.

**Error 404**
```json
{
  "message": "Batch not found",
  "errors": []
}
```

---

## Kardex

Append-only audit ledger. One entry per movement. Never updated or deleted.

### GET /api/v1/inventory/kardex/

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `size` | int | Page size |
| `ingredient_id` | UUID | Filter by ingredient |
| `location_id` | UUID | Filter by location |
| `movement_type` | string | Filter by movement type |

```bash
# Full kardex for one ingredient at one location
curl "http://localhost:8000/api/v1/inventory/kardex/?ingredient_id=a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11&location_id=11111111-0000-0000-0000-000000000001"

# All adjustment entries
curl "http://localhost:8000/api/v1/inventory/kardex/?movement_type=adjustment"
```

**Response 200**
```json
{
  "data": {
    "items": [
      {
        "entity_id": "55555555-0000-0000-0000-000000000001",
        "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "location_id": "11111111-0000-0000-0000-000000000001",
        "movement_id": "33333333-0000-0000-0000-000000000001",
        "movement_date": "2025-07-25T10:00:00Z",
        "movement_type": "entry",
        "quantity_in": "50.0000",
        "quantity_out": "0.0000",
        "quantity_balance": "50.0000",
        "unit_cost": "1.5000",
        "total_value_change": "75.0000",
        "balance_value": "75.0000",
        "created_at": "2025-07-25T10:00:00Z",
        "updated_at": "2025-07-25T10:00:00Z"
      },
      {
        "entity_id": "55555555-0000-0000-0000-000000000002",
        "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "location_id": "11111111-0000-0000-0000-000000000001",
        "movement_id": "33333333-0000-0000-0000-000000000002",
        "movement_date": "2025-07-25T11:00:00Z",
        "movement_type": "exit",
        "quantity_in": "0.0000",
        "quantity_out": "10.0000",
        "quantity_balance": "40.0000",
        "unit_cost": "1.5000",
        "total_value_change": "-15.0000",
        "balance_value": "60.0000",
        "created_at": "2025-07-25T11:00:00Z",
        "updated_at": "2025-07-25T11:00:00Z"
      }
    ],
    "total": 2,
    "page": 1,
    "size": 20,
    "pages": 1
  }
}
```

**Kardex fields explained**

| Field | Description |
|-------|-------------|
| `quantity_in` | Units added this movement (0 for exits) |
| `quantity_out` | Units removed this movement (0 for entries) |
| `quantity_balance` | Running total after this movement |
| `unit_cost` | Cost per unit at time of movement |
| `total_value_change` | `(quantity_in - quantity_out) × unit_cost` — negative for exits |
| `balance_value` | `quantity_balance × unit_cost` — total stock value after movement |

---

### GET /api/v1/inventory/kardex/ingredient/{ingredient_id}

All kardex entries for one ingredient across all locations. Supports optional `location_id` filter.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `size` | int | Page size |
| `location_id` | UUID | Narrow to a specific location |

```bash
# All kardex entries for an ingredient
curl "http://localhost:8000/api/v1/inventory/kardex/ingredient/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"

# Same, filtered to one location
curl "http://localhost:8000/api/v1/inventory/kardex/ingredient/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11?location_id=11111111-0000-0000-0000-000000000001"
```

**Response 200** — same shape as `GET /kardex/`.

---

## Error Reference

| HTTP Status | `error_code` | When it happens |
|-------------|--------------|-----------------|
| 400 | `insufficient_stock` | Exit/deduction quantity exceeds `quantity_available` |
| 400 | `location_in_use` | Deleting a location that still has stock items |
| 400 | `batch_expired` | Reserved for future expiry enforcement logic |
| 404 | `not_found` | Resource not found by ID or ingredient+location pair |
| 409 | `conflict` | Creating a location with a duplicate code |
| 422 | `unprocessable_entity` | Pydantic validation failed (wrong type, missing field, etc.) |

**Validation error example (422)**
```json
{
  "message": "Validation error",
  "errors": [
    {
      "field": "quantity",
      "message": "Input should be greater than 0"
    },
    {
      "field": "location_type",
      "message": "Input should be 'warehouse', 'fridge', 'freezer', 'bar' or 'production'"
    }
  ]
}
```

---

## End-to-end Test Sequence

Run these in order to test the full inventory workflow.

```bash
BASE_CAT="http://localhost:8000/api/v1/catalog"
BASE_INV="http://localhost:8000/api/v1/inventory"

# ── Prerequisites: create catalog master data ──────────────────────────────

# 1. Create unit of measure
KG=$(curl -s -X POST $BASE_CAT/units/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Kilogram","abbreviation":"kg","unit_type":"weight"}')
KG_ID=$(echo $KG | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['entity_id'])")
echo "Unit: $KG_ID"

# 2. Create category
CAT=$(curl -s -X POST $BASE_CAT/categories/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Vegetables"}')
CAT_ID=$(echo $CAT | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['entity_id'])")
echo "Category: $CAT_ID"

# 3. Create ingredient (reorder_point=5)
ING=$(curl -s -X POST $BASE_CAT/ingredients/ \
  -H "Content-Type: application/json" \
  -d "{\"sku\":\"VEG-001\",\"name\":\"Tomato\",\"category_id\":\"$CAT_ID\",\"unit_of_measure_id\":\"$KG_ID\",\"reorder_point\":\"5\",\"cost_per_unit\":\"1.50\"}")
ING_ID=$(echo $ING | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['entity_id'])")
echo "Ingredient: $ING_ID"

# ── Inventory setup ────────────────────────────────────────────────────────

# 4. Create a storage location
LOC=$(curl -s -X POST $BASE_INV/locations/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Main Warehouse","code":"WH-01","location_type":"warehouse"}')
LOC_ID=$(echo $LOC | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['entity_id'])")
echo "Location: $LOC_ID"

# ── Stock entry ────────────────────────────────────────────────────────────

# 5. Record a stock entry (50 kg, batch 1)
MOV1=$(curl -s -X POST $BASE_INV/movements/entry \
  -H "Content-Type: application/json" \
  -d "{
    \"ingredient_id\": \"$ING_ID\",
    \"location_id\": \"$LOC_ID\",
    \"quantity\": \"50.00\",
    \"unit_cost\": \"1.50\",
    \"batch_number\": \"BATCH-001\",
    \"received_date\": \"2025-07-25\"
  }")
echo "Entry movement: $(echo $MOV1 | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['entity_id'])")"

# 6. Record a second entry (20 kg, batch 2 — older batch, different cost)
curl -s -X POST $BASE_INV/movements/entry \
  -H "Content-Type: application/json" \
  -d "{
    \"ingredient_id\": \"$ING_ID\",
    \"location_id\": \"$LOC_ID\",
    \"quantity\": \"20.00\",
    \"unit_cost\": \"1.45\",
    \"batch_number\": \"BATCH-002\",
    \"received_date\": \"2025-07-20\"
  }" > /dev/null

# 7. Check stock (should be 70 kg on hand)
echo "--- Stock levels ---"
curl -s "$BASE_INV/stock/?ingredient_id=$ING_ID" | python3 -m json.tool

# ── Stock exit (FIFO) ──────────────────────────────────────────────────────

# 8. Record a stock exit (25 kg — should consume BATCH-002 fully then 5 kg from BATCH-001)
curl -s -X POST $BASE_INV/movements/exit \
  -H "Content-Type: application/json" \
  -d "{
    \"ingredient_id\": \"$ING_ID\",
    \"location_id\": \"$LOC_ID\",
    \"quantity\": \"25.00\",
    \"reason\": \"Kitchen request\"
  }" | python3 -m json.tool

# 9. Check batches (BATCH-002 should be 0 kg, BATCH-001 should be 45 kg)
echo "--- Batches after exit ---"
curl -s "$BASE_INV/batches/?ingredient_id=$ING_ID" | python3 -m json.tool

# ── Stock adjustment ───────────────────────────────────────────────────────

# 10. Record a negative adjustment (found 2 kg spoilage)
curl -s -X POST $BASE_INV/movements/adjustment \
  -H "Content-Type: application/json" \
  -d "{
    \"ingredient_id\": \"$ING_ID\",
    \"location_id\": \"$LOC_ID\",
    \"quantity_delta\": \"-2.00\",
    \"reason\": \"Spoilage found during inspection\"
  }" | python3 -m json.tool

# ── Kardex audit trail ─────────────────────────────────────────────────────

# 11. View full kardex (4 entries: 2 entries + 1 exit + 1 adjustment)
echo "--- Kardex ---"
curl -s "$BASE_INV/kardex/ingredient/$ING_ID?location_id=$LOC_ID" | python3 -m json.tool

# ── Low-stock alert ────────────────────────────────────────────────────────

# 12. Drain most of the stock to trigger low-stock (exit 38 kg — leaves 3 kg, below reorder_point=5)
curl -s -X POST $BASE_INV/movements/exit \
  -H "Content-Type: application/json" \
  -d "{
    \"ingredient_id\": \"$ING_ID\",
    \"location_id\": \"$LOC_ID\",
    \"quantity\": \"38.00\",
    \"reason\": \"Bulk kitchen use\"
  }" > /dev/null

echo "--- Low-stock items ---"
curl -s $BASE_INV/stock/low-stock | python3 -m json.tool

# ── Insufficient stock guard ───────────────────────────────────────────────

# 13. Try to exit more than available (should return 400)
echo "--- Expected 400 ---"
curl -s -X POST $BASE_INV/movements/exit \
  -H "Content-Type: application/json" \
  -d "{
    \"ingredient_id\": \"$ING_ID\",
    \"location_id\": \"$LOC_ID\",
    \"quantity\": \"999.00\"
  }" | python3 -m json.tool
```

---

## FIFO Batch Deduction

When an exit movement is recorded, batches are consumed in this order:

1. `received_date ASC` — oldest received batch first
2. `expiry_date ASC NULLS LAST` — if same received date, soonest to expire first; batches with no expiry date are last

Each batch is drained to 0 before moving to the next. If the exit quantity spans multiple batches, the `batch_id` on the resulting `StockMovement` references the first (oldest) batch consumed.

**Example:** 3 batches exist for the same ingredient+location:

| batch | received_date | expiry_date | quantity |
|-------|--------------|-------------|----------|
| A | 2025-07-10 | 2025-09-01 | 20 |
| B | 2025-07-10 | 2025-08-15 | 15 |
| C | 2025-07-20 | null | 30 |

Exit of 25 kg consumes: **B (15) → A (10)**. Result: B=0, A=10, C=30.
