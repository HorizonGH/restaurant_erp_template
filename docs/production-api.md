# Production Module — API Reference

The production module manages the full recipe-to-output lifecycle: defining recipes with ingredient bills-of-materials, creating production orders, tracking execution, and recording actual yield versus expected.

---

## Business Concepts

| Concept | Description |
|---|---|
| **Recipe** | A bill of materials (BOM): the exact ingredients and quantities required to produce a defined yield. Each update bumps the `version` field so production orders can detect stale recipes. |
| **Recipe Ingredient** | One line in the BOM — an ingredient, its required quantity, and the unit of measure for that quantity. |
| **Production Order** | An instruction to produce a specific number of recipe yields from a source location. Automatically pre-populates order lines from the recipe and snapshots current stock availability. Auto-numbered `PRD-YYYYMM-XXXXX`. |
| **Production Order Line** | One ingredient requirement derived from the recipe, scaled by `quantity_to_produce`. Tracks `required_quantity`, `available_quantity` (live snapshot), and `consumed_quantity` (actual at completion). |
| **Yield Record** | Immutable record created when an order completes — captures `expected_yield` (recipe yield × quantity_to_produce) vs `actual_yield`, variance, and variance %. |

---

## Production Order Lifecycle

```
draft ──confirm──► confirmed ──start──► in_progress ──complete──► completed
  │         │                    │                                   (yield record created)
  │      raises if               │
  │   stock insufficient     (movements fired on complete)
  │
  └──cancel──► cancelled  (from any non-completed state)
```

| Status | Meaning |
|---|---|
| `draft` | Order created. `quantity_to_produce` and scheduling can still be edited. |
| `confirmed` | Stock availability verified. Order locked — no more edits. |
| `in_progress` | Production has started. `started_at` timestamp set. |
| `completed` | All ingredient exit movements fired. `YieldRecord` created. `completed_at` set. |
| `cancelled` | Voided before completion. No movements fired. |

### What happens at `complete`

For every order line:
1. A **`production_consumption`** inventory exit movement is recorded.
2. `consumed_quantity` is set to `required_quantity`.

A `YieldRecord` is then created comparing `expected_yield` (from recipe) to `actual_yield` (supplied by the caller).

---

## Base URL

```
/api/v1/production
```

---

## Recipes

### List all active recipes (select)

```
GET /recipes/select
```

Returns a lightweight list of all active recipes for dropdowns.

**Response** `200 OK`
```json
{
  "data": [
    {
      "entity_id": "rec-uuid",
      "name": "Beef Tenderloin Medallions",
      "version": 3,
      "yield_quantity": "4.0000",
      "yield_unit_id": "uom-uuid",
      "output_ingredient_id": null,
      "is_active": true,
      "description": null,
      "notes": null
    }
  ]
}
```

---

### List recipes (paginated)

```
GET /recipes
```

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `page` | int | Page number (default 1) |
| `size` | int | Page size (default 20, max 100) |
| `name` | string | Partial-match search on recipe name |
| `is_active` | bool | Filter by active status |
| `ordering` | string | `name`, `created_at` (prefix `-` for desc) |

**Response** `200 OK`
```json
{
  "data": {
    "items": [ ... ],
    "total": 5,
    "page": 1,
    "size": 20,
    "pages": 1
  }
}
```

---

### Create recipe

```
POST /recipes
```

**Body**
```json
{
  "name": "Beef Tenderloin Medallions",
  "description": "Pan-seared with olive oil, salt and pepper",
  "yield_quantity": 4,
  "yield_unit_id": "<uom-uuid>",
  "output_ingredient_id": null,
  "is_active": true,
  "notes": null
}
```

**Response** `201 Created`

**Errors**

| Code | Meaning |
|---|---|
| `conflict` | Recipe name already exists |
| `not_found` | `yield_unit_id` or `output_ingredient_id` not found |

---

### Get recipe

```
GET /recipes/{recipe_id}
```

---

### Update recipe

```
PATCH /recipes/{recipe_id}
```

Every update increments `version`. All fields are optional.

**Body**
```json
{
  "yield_quantity": 6,
  "notes": "Updated for larger batch"
}
```

---

### Delete recipe

```
DELETE /recipes/{recipe_id}
```

Soft-deletes the recipe. Fails if any production orders reference it.

Returns `204 No Content`.

**Errors**

| Code | Meaning |
|---|---|
| `recipe_in_use` | Recipe has associated production orders |

---

### Activate / Deactivate recipe

```
PATCH /recipes/{recipe_id}/activate
PATCH /recipes/{recipe_id}/deactivate
```

---

## Recipe Ingredients

### List ingredients

```
GET /recipes/{recipe_id}/ingredients
```

**Response** `200 OK`
```json
{
  "data": [
    {
      "entity_id": "ri-uuid",
      "recipe_id": "rec-uuid",
      "ingredient_id": "ing-uuid",
      "quantity": "0.3500",
      "unit_of_measure_id": "uom-uuid",
      "notes": null
    }
  ]
}
```

---

### Add ingredient to recipe

```
POST /recipes/{recipe_id}/ingredients
```

**Body**
```json
{
  "ingredient_id": "<ing-uuid>",
  "quantity": 0.35,
  "unit_of_measure_id": "<uom-uuid>",
  "notes": null
}
```

**Response** `201 Created`

Also increments recipe `version`.

**Errors**

| Code | Meaning |
|---|---|
| `conflict` | Ingredient already in this recipe |
| `not_found` | `ingredient_id` or `unit_of_measure_id` not found |

---

### Update recipe ingredient

```
PATCH /recipes/{recipe_id}/ingredients/{ingredient_line_id}
```

Fields: `quantity`, `unit_of_measure_id`, `notes`. Increments recipe `version`.

---

### Remove ingredient from recipe

```
DELETE /recipes/{recipe_id}/ingredients/{ingredient_line_id}
```

Returns `204 No Content`. Increments recipe `version`.

---

## Production Orders

### List orders (paginated)

```
GET /orders
```

**Query parameters**

| Parameter | Type | Description |
|---|---|---|
| `page` | int | Page number (default 1) |
| `size` | int | Page size (default 20, max 100) |
| `recipe_id` | UUID | Filter by recipe |
| `source_location_id` | UUID | Filter by source location |
| `status` | string | Filter by order status |
| `ordering` | string | `scheduled_date`, `created_at` |

---

### Create production order

```
POST /orders
```

Automatically pre-populates order lines from the recipe (scaled to `quantity_to_produce`) and snapshots current availability from the source location.

**Body**
```json
{
  "recipe_id": "<rec-uuid>",
  "source_location_id": "<loc-uuid>",
  "quantity_to_produce": 2,
  "scheduled_date": "2025-07-26",
  "notes": "Dinner service prep"
}
```

**Response** `201 Created`

**Errors**

| Code | Meaning |
|---|---|
| `recipe_in_use` | Recipe is inactive |
| `empty_recipe` | Recipe has no ingredients |
| `not_found` | `recipe_id` or `source_location_id` not found |

---

### Get order

```
GET /orders/{order_id}
```

---

### Update order

```
PATCH /orders/{order_id}
```

Only allowed on `draft` orders. Changing `quantity_to_produce` automatically recalculates `required_quantity` and refreshes `available_quantity` on all order lines.

**Body**
```json
{
  "quantity_to_produce": 4,
  "scheduled_date": "2025-07-27"
}
```

---

### Confirm order

```
POST /orders/{order_id}/confirm
```

Transitions `draft` → `confirmed`.

1. Refreshes the `available_quantity` snapshot on every line.
2. Raises `insufficient_stock_for_production` listing all shortages if any ingredient is unavailable.

**Errors**

| Code | Meaning |
|---|---|
| `order_not_draft` | Order is not in draft |
| `empty_production_order` | Order has no lines |
| `insufficient_stock_for_production` | One or more ingredients short |

---

### Start order

```
POST /orders/{order_id}/start
```

Transitions `confirmed` → `in_progress`. Sets `started_at`.

---

### Complete order

```
POST /orders/{order_id}/complete
```

Transitions `in_progress` → `completed`.

**Body**
```json
{
  "actual_yield": 7.5,
  "notes": "One portion slightly under spec"
}
```

Fires one `production_consumption` exit movement per order line. Creates a `YieldRecord`. Sets `completed_at`.

---

### Cancel order

```
POST /orders/{order_id}/cancel
```

Cancels from any non-completed state. No inventory movements are reversed.

---

### Check availability

```
GET /orders/{order_id}/availability
```

Refreshes and returns the current stock availability for all order lines without changing order status.

**Response** `200 OK`
```json
{
  "data": {
    "order_id": "ord-uuid",
    "all_available": false,
    "lines": [
      {
        "ingredient_id": "ing-uuid",
        "required_quantity": "0.7000",
        "available_quantity": "5.2000",
        "is_available": true,
        "shortage": "0.0000"
      },
      {
        "ingredient_id": "ing-uuid-2",
        "required_quantity": "10.0000",
        "available_quantity": "6.3000",
        "is_available": false,
        "shortage": "3.7000"
      }
    ]
  }
}
```

---

### List order lines

```
GET /orders/{order_id}/lines
```

**Response** `200 OK`
```json
{
  "data": [
    {
      "entity_id": "line-uuid",
      "order_id": "ord-uuid",
      "ingredient_id": "ing-uuid",
      "required_quantity": "0.7000",
      "consumed_quantity": "0.7000",
      "available_quantity": "5.2000",
      "is_available": true,
      "shortage": "0.0000"
    }
  ]
}
```

---

### Get yield record

```
GET /orders/{order_id}/yield
```

Available only after the order is `completed`.

**Response** `200 OK`
```json
{
  "data": {
    "entity_id": "yr-uuid",
    "order_id": "ord-uuid",
    "expected_yield": "8.0000",
    "actual_yield": "7.5000",
    "variance": "-0.5000",
    "variance_percentage": "-6.25",
    "notes": "One portion slightly under spec"
  }
}
```

---

## Error Reference

| Error code | HTTP | When raised |
|---|---|---|
| `recipe_in_use` | 400 | Deleting a recipe with production orders, or creating an order for an inactive recipe |
| `empty_recipe` | 400 | Creating an order from a recipe with no ingredients |
| `order_not_draft` | 400 | Operation requires draft status |
| `order_not_confirmed` | 400 | `start` requires confirmed status |
| `order_not_in_progress` | 400 | `complete` requires in_progress status |
| `order_already_completed` | 400 | Order is already completed |
| `order_already_cancelled` | 400 | Order is already cancelled |
| `insufficient_stock_for_production` | 400 | One or more ingredients below required at confirm time |
| `empty_production_order` | 400 | Order has no lines |
| `not_found` | 404 | Any resource not found |
| `conflict` | 409 | Duplicate recipe name or duplicate ingredient in recipe |

---

## End-to-End Example

```bash
BASE="http://localhost:8000/api/v1"

# 1. Create a recipe
RECIPE=$(curl -s -X POST "$BASE/production/recipes" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Beef Tenderloin Medallions",
    "yield_quantity": 4,
    "yield_unit_id": "<por-uom-uuid>"
  }')
RECIPE_ID=$(echo $RECIPE | jq -r '.data.entity_id')

# 2. Add ingredients
curl -s -X POST "$BASE/production/recipes/$RECIPE_ID/ingredients" \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id": "<beef-uuid>", "quantity": 0.35, "unit_of_measure_id": "<kg-uom-uuid>"}'

curl -s -X POST "$BASE/production/recipes/$RECIPE_ID/ingredients" \
  -H "Content-Type: application/json" \
  -d '{"ingredient_id": "<salt-uuid>", "quantity": 8, "unit_of_measure_id": "<g-uom-uuid>"}'

# 3. Create a production order (produces 2 recipe yields = 8 portions)
ORDER=$(curl -s -X POST "$BASE/production/orders" \
  -H "Content-Type: application/json" \
  -d "{
    \"recipe_id\": \"$RECIPE_ID\",
    \"source_location_id\": \"<freezer-uuid>\",
    \"quantity_to_produce\": 2,
    \"scheduled_date\": \"$(date +%Y-%m-%d)\"
  }")
ORDER_ID=$(echo $ORDER | jq -r '.data.entity_id')

# 4. Check availability before confirming
curl -s "$BASE/production/orders/$ORDER_ID/availability" | jq '.data'

# 5. Confirm (validates stock — raises 400 if any ingredient is short)
curl -s -X POST "$BASE/production/orders/$ORDER_ID/confirm"

# 6. Start production
curl -s -X POST "$BASE/production/orders/$ORDER_ID/start"

# 7. Complete production with actual yield
curl -s -X POST "$BASE/production/orders/$ORDER_ID/complete" \
  -H "Content-Type: application/json" \
  -d '{"actual_yield": 7.5, "notes": "Slight under-yield"}'
# → production_consumption movements fired for all lines

# 8. Review yield record
curl -s "$BASE/production/orders/$ORDER_ID/yield" | jq '.data'
```
