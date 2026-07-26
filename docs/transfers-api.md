# Transfers & Physical Counts API Reference

Base URL: `http://localhost:8000/api/v1/transfers`

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
  "errors": []
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

## Transfers

A transfer moves stock from one location to another within the same business. It goes through a three-step lifecycle:

```
draft → in_transit → completed
  └────────────────→ cancelled
```

- **draft** — being built; lines can be added, updated, or removed
- **in_transit** — stock availability has been validated; awaiting physical delivery
- **completed** — goods received; stock movements have been recorded
- **cancelled** — abandoned; no stock movements are created

---

### GET /api/v1/transfers/transfers/

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default 1) |
| `size` | int | Page size (default 20) |
| `from_location_id` | UUID | Filter by source location |
| `to_location_id` | UUID | Filter by destination location |
| `status` | string | Filter by status (`draft`, `in_transit`, `completed`, `cancelled`) |

```bash
# All in-transit transfers
curl "http://localhost:8000/api/v1/transfers/transfers/?status=in_transit"

# All transfers from the main warehouse
curl "http://localhost:8000/api/v1/transfers/transfers/?from_location_id=11111111-0000-0000-0000-000000000001"
```

**Response 200**
```json
{
  "data": {
    "items": [
      {
        "entity_id": "aaaa0001-0000-0000-0000-000000000001",
        "transfer_number": "TRF-202507-A3F9B2",
        "from_location_id": "11111111-0000-0000-0000-000000000001",
        "to_location_id": "11111111-0000-0000-0000-000000000002",
        "status": "draft",
        "notes": null,
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

### POST /api/v1/transfers/transfers/

Create a draft transfer. The `transfer_number` is auto-generated (`TRF-YYYYMM-XXXXXX`).

**Full body**
```json
{
  "from_location_id": "11111111-0000-0000-0000-000000000001",
  "to_location_id": "11111111-0000-0000-0000-000000000002",
  "notes": "Weekly restock from warehouse to kitchen"
}
```

**Minimal body**
```json
{
  "from_location_id": "11111111-0000-0000-0000-000000000001",
  "to_location_id": "11111111-0000-0000-0000-000000000002"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/transfers/transfers/ \
  -H "Content-Type: application/json" \
  -d '{
    "from_location_id": "11111111-0000-0000-0000-000000000001",
    "to_location_id": "11111111-0000-0000-0000-000000000002",
    "notes": "Weekly restock"
  }'
```

**Response 201**
```json
{
  "data": {
    "entity_id": "aaaa0001-0000-0000-0000-000000000001",
    "transfer_number": "TRF-202507-A3F9B2",
    "from_location_id": "11111111-0000-0000-0000-000000000001",
    "to_location_id": "11111111-0000-0000-0000-000000000002",
    "status": "draft",
    "notes": "Weekly restock",
    "created_at": "2025-07-25T10:00:00Z",
    "updated_at": "2025-07-25T10:00:00Z"
  }
}
```

**Error 409 — same source and destination**
```json
{
  "message": "Source and destination locations must be different",
  "errors": []
}
```

---

### GET /api/v1/transfers/transfers/{transfer_id}

```bash
curl http://localhost:8000/api/v1/transfers/transfers/aaaa0001-0000-0000-0000-000000000001
```

**Response 200** — same shape as the item in the list response.

---

### PATCH /api/v1/transfers/transfers/{transfer_id}

Only allowed while the transfer is in `draft` status. Only `notes` can be updated; to change locations, cancel and recreate.

**Body**
```json
{
  "notes": "Updated: urgent restock for dinner service"
}
```

```bash
curl -X PATCH http://localhost:8000/api/v1/transfers/transfers/aaaa0001-0000-0000-0000-000000000001 \
  -H "Content-Type: application/json" \
  -d '{"notes": "Updated: urgent restock for dinner service"}'
```

**Response 200** — updated transfer object.

**Error 400 — not in draft**
```json
{
  "message": "Only draft transfers can be updated",
  "errors": []
}
```

---

### POST /api/v1/transfers/transfers/{transfer_id}/send

Validates that all lines have sufficient available stock at the source location, then transitions to `in_transit`. **No stock is moved yet.**

```bash
curl -X POST http://localhost:8000/api/v1/transfers/transfers/aaaa0001-0000-0000-0000-000000000001/send
```

**Response 200**
```json
{
  "data": {
    "entity_id": "aaaa0001-0000-0000-0000-000000000001",
    "transfer_number": "TRF-202507-A3F9B2",
    "status": "in_transit",
    ...
  }
}
```

**Error 400 — no lines**
```json
{
  "message": "Transfer has no lines — add items before sending",
  "errors": []
}
```

**Error 400 — insufficient stock**
```json
{
  "message": "Insufficient stock for ingredient a0eebc99-...: available=3.0000, requested=10.0000",
  "errors": []
}
```

---

### POST /api/v1/transfers/transfers/{transfer_id}/receive

Executes the transfer: for each line, records a `transfer_out` exit from the source location and a `transfer_in` entry into the destination location. Updates the kardex for both locations.

```bash
curl -X POST http://localhost:8000/api/v1/transfers/transfers/aaaa0001-0000-0000-0000-000000000001/receive
```

**Response 200**
```json
{
  "data": {
    "entity_id": "aaaa0001-0000-0000-0000-000000000001",
    "transfer_number": "TRF-202507-A3F9B2",
    "status": "completed",
    ...
  }
}
```

**Error 400 — not in transit**
```json
{
  "message": "Only in-transit transfers can be received",
  "errors": []
}
```

---

### POST /api/v1/transfers/transfers/{transfer_id}/cancel

Cancels a `draft` or `in_transit` transfer. No stock movements are created or reversed.

```bash
curl -X POST http://localhost:8000/api/v1/transfers/transfers/aaaa0001-0000-0000-0000-000000000001/cancel
```

**Response 200** — transfer object with `"status": "cancelled"`.

**Error 400 — already completed**
```json
{
  "message": "Completed transfers cannot be cancelled",
  "errors": []
}
```

---

## Transfer Lines

Lines define what ingredients and quantities are being transferred. They can only be managed while the transfer is in `draft` status.

---

### GET /api/v1/transfers/transfers/{transfer_id}/lines

```bash
curl http://localhost:8000/api/v1/transfers/transfers/aaaa0001-0000-0000-0000-000000000001/lines
```

**Response 200**
```json
{
  "data": [
    {
      "entity_id": "bbbb0001-0000-0000-0000-000000000001",
      "transfer_id": "aaaa0001-0000-0000-0000-000000000001",
      "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "batch_id": null,
      "requested_quantity": "10.0000",
      "transferred_quantity": "0.0000",
      "created_at": "2025-07-25T10:00:00Z",
      "updated_at": "2025-07-25T10:00:00Z"
    }
  ]
}
```

> `transferred_quantity` stays `0` until `receive` is called, then it equals `requested_quantity`.

---

### POST /api/v1/transfers/transfers/{transfer_id}/lines

**Full body** (with optional specific batch)
```json
{
  "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "requested_quantity": "10.00",
  "batch_id": "44444444-0000-0000-0000-000000000001"
}
```

**Minimal body** (FIFO batch selection on receive)
```json
{
  "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "requested_quantity": "10.00"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/transfers/transfers/aaaa0001-0000-0000-0000-000000000001/lines \
  -H "Content-Type: application/json" \
  -d '{
    "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "requested_quantity": "10.00"
  }'
```

**Response 201** — the created line object.

**Error 409 — duplicate ingredient**
```json
{
  "message": "This ingredient already has a line on this transfer",
  "errors": []
}
```

---

### PATCH /api/v1/transfers/transfers/{transfer_id}/lines/{line_id}

Update the quantity or assigned batch on a draft line.

**Body** — all fields optional
```json
{
  "requested_quantity": "15.00",
  "batch_id": null
}
```

```bash
curl -X PATCH \
  "http://localhost:8000/api/v1/transfers/transfers/aaaa0001-0000-0000-0000-000000000001/lines/bbbb0001-0000-0000-0000-000000000001" \
  -H "Content-Type: application/json" \
  -d '{"requested_quantity": "15.00"}'
```

**Response 200** — updated line object.

---

### DELETE /api/v1/transfers/transfers/{transfer_id}/lines/{line_id}

Soft-deletes a line from a draft transfer.

```bash
curl -X DELETE \
  "http://localhost:8000/api/v1/transfers/transfers/aaaa0001-0000-0000-0000-000000000001/lines/bbbb0001-0000-0000-0000-000000000001"
```

**Response 204** — no body.

---

## Physical Counts

A physical count reconciles what the system believes is in stock with what staff physically counted on the shelves.

```
in_progress → completed
     └──────→ cancelled
```

- **in_progress** — count is open; staff can submit counted quantities line by line
- **completed** — variances applied as `adjustment` movements to the inventory
- **cancelled** — abandoned without any stock changes

---

### GET /api/v1/transfers/counts/

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `size` | int | Page size |
| `location_id` | UUID | Filter by location |
| `status` | string | Filter by status (`in_progress`, `completed`, `cancelled`) |

```bash
# All in-progress counts at the walk-in fridge
curl "http://localhost:8000/api/v1/transfers/counts/?location_id=11111111-0000-0000-0000-000000000002&status=in_progress"
```

**Response 200**
```json
{
  "data": {
    "items": [
      {
        "entity_id": "cccc0001-0000-0000-0000-000000000001",
        "location_id": "11111111-0000-0000-0000-000000000002",
        "status": "in_progress",
        "notes": "Weekly fridge count",
        "created_at": "2025-07-25T08:00:00Z",
        "updated_at": "2025-07-25T08:00:00Z"
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

### POST /api/v1/transfers/counts/

Creates the count and **automatically snapshots** the current `quantity_on_hand` for all active stock items at the location into count lines. If `ingredient_ids` is provided, only those ingredients are snapshotted.

**Full body** (all ingredients at location)
```json
{
  "location_id": "11111111-0000-0000-0000-000000000002",
  "notes": "Weekly fridge count"
}
```

**Partial body** (specific ingredients only)
```json
{
  "location_id": "11111111-0000-0000-0000-000000000002",
  "notes": "Spot check — dairy only",
  "ingredient_ids": [
    "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12"
  ]
}
```

```bash
curl -X POST http://localhost:8000/api/v1/transfers/counts/ \
  -H "Content-Type: application/json" \
  -d '{
    "location_id": "11111111-0000-0000-0000-000000000002",
    "notes": "Weekly fridge count"
  }'
```

**Response 201**
```json
{
  "data": {
    "entity_id": "cccc0001-0000-0000-0000-000000000001",
    "location_id": "11111111-0000-0000-0000-000000000002",
    "status": "in_progress",
    "notes": "Weekly fridge count",
    "created_at": "2025-07-25T08:00:00Z",
    "updated_at": "2025-07-25T08:00:00Z"
  }
}
```

---

### GET /api/v1/transfers/counts/{count_id}

```bash
curl http://localhost:8000/api/v1/transfers/counts/cccc0001-0000-0000-0000-000000000001
```

**Response 200** — same shape as the item in the list response.

---

### PATCH /api/v1/transfers/counts/{count_id}

Only allowed while `in_progress`. Only `notes` can be updated.

```bash
curl -X PATCH http://localhost:8000/api/v1/transfers/counts/cccc0001-0000-0000-0000-000000000001 \
  -H "Content-Type: application/json" \
  -d '{"notes": "Updated: fridge count including beverages"}'
```

**Response 200** — updated count object.

---

### POST /api/v1/transfers/counts/{count_id}/complete

Applies variances: for each line where `counted_quantity ≠ system_quantity`, fires an `adjustment` movement with `movement_type = physical_count`. Lines where `counted_quantity` is still `null` (not yet recorded) are skipped.

```bash
curl -X POST http://localhost:8000/api/v1/transfers/counts/cccc0001-0000-0000-0000-000000000001/complete
```

**Response 200**
```json
{
  "data": {
    "entity_id": "cccc0001-0000-0000-0000-000000000001",
    "location_id": "11111111-0000-0000-0000-000000000002",
    "status": "completed",
    ...
  }
}
```

**Error 400 — no lines counted yet**
```json
{
  "message": "No lines have been counted yet — record at least one counted quantity",
  "errors": []
}
```

---

### POST /api/v1/transfers/counts/{count_id}/cancel

Cancels an in-progress count. No stock movements are created.

```bash
curl -X POST http://localhost:8000/api/v1/transfers/counts/cccc0001-0000-0000-0000-000000000001/cancel
```

**Response 200** — count object with `"status": "cancelled"`.

---

## Physical Count Lines

Lines are created automatically when the count is opened (one line per stock item at the location). Staff updates each line by submitting the physically counted quantity.

---

### GET /api/v1/transfers/counts/{count_id}/lines

```bash
curl http://localhost:8000/api/v1/transfers/counts/cccc0001-0000-0000-0000-000000000001/lines
```

**Response 200**
```json
{
  "data": [
    {
      "entity_id": "dddd0001-0000-0000-0000-000000000001",
      "count_id": "cccc0001-0000-0000-0000-000000000001",
      "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "system_quantity": "30.0000",
      "counted_quantity": null,
      "variance": null,
      "created_at": "2025-07-25T08:00:00Z",
      "updated_at": "2025-07-25T08:00:00Z"
    },
    {
      "entity_id": "dddd0001-0000-0000-0000-000000000002",
      "count_id": "cccc0001-0000-0000-0000-000000000001",
      "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12",
      "system_quantity": "8.0000",
      "counted_quantity": "7.5000",
      "variance": "-0.5000",
      "created_at": "2025-07-25T08:00:00Z",
      "updated_at": "2025-07-25T08:30:00Z"
    }
  ]
}
```

**Line fields explained**

| Field | Description |
|-------|-------------|
| `system_quantity` | Snapshot of `quantity_on_hand` at the moment the count was opened — never changes |
| `counted_quantity` | What staff physically counted — `null` until submitted |
| `variance` | `counted - system`; negative = loss/shrinkage; positive = surplus; `null` if not yet counted |

---

### PATCH /api/v1/transfers/counts/{count_id}/lines/{line_id}

Submit or update the physically counted quantity for a line. Can be called multiple times before completing the count.

**Body**
```json
{
  "counted_quantity": "7.50"
}
```

```bash
curl -X PATCH \
  "http://localhost:8000/api/v1/transfers/counts/cccc0001-0000-0000-0000-000000000001/lines/dddd0001-0000-0000-0000-000000000002" \
  -H "Content-Type: application/json" \
  -d '{"counted_quantity": "7.50"}'
```

**Response 200**
```json
{
  "data": {
    "entity_id": "dddd0001-0000-0000-0000-000000000002",
    "count_id": "cccc0001-0000-0000-0000-000000000001",
    "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12",
    "system_quantity": "8.0000",
    "counted_quantity": "7.5000",
    "variance": "-0.5000",
    "created_at": "2025-07-25T08:00:00Z",
    "updated_at": "2025-07-25T08:30:00Z"
  }
}
```

**Error 400 — count not in progress**
```json
{
  "message": "Counted quantities can only be recorded on in-progress counts",
  "errors": []
}
```

---

## Error Reference

| HTTP Status | `error_code` | When it happens |
|-------------|--------------|-----------------|
| 400 | `transfer_not_draft` | Editing/adding lines/sending a non-draft transfer |
| 400 | `transfer_not_in_transit` | Receiving a transfer that isn't in_transit |
| 400 | `transfer_already_completed` | Cancelling a completed transfer |
| 400 | `transfer_already_cancelled` | Cancelling an already-cancelled transfer |
| 400 | `empty_transfer` | Sending a transfer with no lines |
| 400 | `insufficient_stock` | Send validation fails — not enough available stock at source |
| 400 | `count_not_in_progress` | Updating/completing/recording a non-in-progress count |
| 400 | `count_already_completed` | Cancelling or completing an already-completed count |
| 400 | `empty_physical_count` | Completing a count with zero recorded lines |
| 404 | `not_found` | Resource not found by ID |
| 409 | `conflict` | Same source and destination; duplicate ingredient on transfer lines |
| 422 | `unprocessable_entity` | Pydantic validation failed |

---

## End-to-end Test Sequences

### Transfer — full lifecycle

```bash
BASE="http://localhost:8000/api/v1"

# ── Prerequisites: get location IDs from inventory ──────────────────────────
LOCATIONS=$(curl -s "$BASE/inventory/locations/select")
WH_ID=$(echo $LOCATIONS | python3 -c "import sys,json; locs=json.load(sys.stdin)['data']; print(next(l['entity_id'] for l in locs if l['code']=='WH-01'))")
FRG_ID=$(echo $LOCATIONS | python3 -c "import sys,json; locs=json.load(sys.stdin)['data']; print(next(l['entity_id'] for l in locs if l['code']=='FRG-01'))")
echo "Warehouse: $WH_ID  Fridge: $FRG_ID"

# ── Get an ingredient ID ─────────────────────────────────────────────────────
ING=$(curl -s "$BASE/catalog/ingredients/?name=Tomato")
ING_ID=$(echo $ING | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['items'][0]['entity_id'])")
echo "Ingredient: $ING_ID"

# 1. Create transfer (draft)
TRF=$(curl -s -X POST "$BASE/transfers/transfers/" \
  -H "Content-Type: application/json" \
  -d "{\"from_location_id\": \"$WH_ID\", \"to_location_id\": \"$FRG_ID\", \"notes\": \"Daily restock\"}")
TRF_ID=$(echo $TRF | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['entity_id'])")
TRF_NUM=$(echo $TRF | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['transfer_number'])")
echo "Transfer: $TRF_ID ($TRF_NUM)"

# 2. Add a line
curl -s -X POST "$BASE/transfers/transfers/$TRF_ID/lines" \
  -H "Content-Type: application/json" \
  -d "{\"ingredient_id\": \"$ING_ID\", \"requested_quantity\": \"5.00\"}" | python3 -m json.tool

# 3. Send (validates stock)
curl -s -X POST "$BASE/transfers/transfers/$TRF_ID/send" | python3 -m json.tool

# 4. Check stock before receive
echo "--- Stock before receive ---"
curl -s "$BASE/inventory/stock/?ingredient_id=$ING_ID" | python3 -m json.tool

# 5. Receive (creates transfer_out + transfer_in movements)
curl -s -X POST "$BASE/transfers/transfers/$TRF_ID/receive" | python3 -m json.tool

# 6. Check stock after receive (should show stock at both locations)
echo "--- Stock after receive ---"
curl -s "$BASE/inventory/stock/$ING_ID/locations" | python3 -m json.tool

# 7. Verify kardex shows transfer_out at warehouse and transfer_in at fridge
echo "--- Kardex (transfer movements) ---"
curl -s "$BASE/inventory/kardex/?ingredient_id=$ING_ID&movement_type=transfer_out" | python3 -m json.tool
curl -s "$BASE/inventory/kardex/?ingredient_id=$ING_ID&movement_type=transfer_in" | python3 -m json.tool
```

---

### Physical Count — full lifecycle

```bash
BASE="http://localhost:8000/api/v1"

# ── Get the fridge location ID ───────────────────────────────────────────────
LOCATIONS=$(curl -s "$BASE/inventory/locations/select")
FRG_ID=$(echo $LOCATIONS | python3 -c "import sys,json; locs=json.load(sys.stdin)['data']; print(next(l['entity_id'] for l in locs if l['code']=='FRG-01'))")
echo "Fridge: $FRG_ID"

# 1. Open a count (snapshots all stock items at the fridge)
COUNT=$(curl -s -X POST "$BASE/transfers/counts/" \
  -H "Content-Type: application/json" \
  -d "{\"location_id\": \"$FRG_ID\", \"notes\": \"Weekly fridge count\"}")
CNT_ID=$(echo $COUNT | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['entity_id'])")
echo "Count: $CNT_ID"

# 2. List lines (shows system_quantity snapshot for each ingredient)
echo "--- Lines (system quantities) ---"
LINES=$(curl -s "$BASE/transfers/counts/$CNT_ID/lines")
echo $LINES | python3 -m json.tool

# 3. Extract a line ID to update
LINE_ID=$(echo $LINES | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['entity_id'])")
SYS_QTY=$(echo $LINES | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['system_quantity'])")
echo "Line: $LINE_ID  System qty: $SYS_QTY"

# 4. Submit counted quantity (simulate finding 0.5 kg less than system)
COUNTED=$(python3 -c "from decimal import Decimal; print(float(Decimal('$SYS_QTY') - Decimal('0.5')))")
curl -s -X PATCH "$BASE/transfers/counts/$CNT_ID/lines/$LINE_ID" \
  -H "Content-Type: application/json" \
  -d "{\"counted_quantity\": \"$COUNTED\"}" | python3 -m json.tool

# 5. Complete the count (applies adjustment movements for variances)
curl -s -X POST "$BASE/transfers/counts/$CNT_ID/complete" | python3 -m json.tool

# 6. Verify the adjustment was written to kardex
echo "--- Kardex (physical_count adjustments) ---"
curl -s "$BASE/inventory/kardex/?movement_type=adjustment&location_id=$FRG_ID" | python3 -m json.tool
```
