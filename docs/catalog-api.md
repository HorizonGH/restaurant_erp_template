# Catalog API Reference

Base URL: `http://localhost:8000/api/v1/catalog`

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
    { "field": "name", "message": "field too short" }
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

## Health Check

### GET /api/v1/health

```bash
curl http://localhost:8000/api/v1/health
```

**Response 200**
```json
{
  "data": { "status": "ok" }
}
```

---

## Categories

### GET /api/v1/catalog/categories/

List categories with optional pagination and parent filter.

**Query parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (≥ 1) |
| `size` | int | 20 | Items per page (1–100) |
| `parent_id` | UUID | — | Filter by parent category |

```bash
# All root categories (no parent)
curl "http://localhost:8000/api/v1/catalog/categories/?page=1&size=20"

# Sub-categories of a specific parent
curl "http://localhost:8000/api/v1/catalog/categories/?parent_id=3fa85f64-5717-4562-b3fc-2c963f66afa6"
```

**Response 200**
```json
{
  "data": {
    "items": [
      {
        "entity_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "name": "Vegetables",
        "description": "Fresh and frozen vegetables",
        "parent_id": null,
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

### POST /api/v1/catalog/categories/

Create a category.

**Full body**
```json
{
  "name": "Vegetables",
  "description": "Fresh and frozen vegetables",
  "parent_id": null
}
```

**Minimal body** (required fields only)
```json
{
  "name": "Vegetables"
}
```

**Sub-category body**
```json
{
  "name": "Leafy Greens",
  "parent_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/catalog/categories/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Vegetables", "description": "Fresh and frozen vegetables"}'
```

**Response 201**
```json
{
  "data": {
    "entity_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Vegetables",
    "description": "Fresh and frozen vegetables",
    "parent_id": null,
    "created_at": "2025-07-25T10:00:00Z",
    "updated_at": "2025-07-25T10:00:00Z"
  }
}
```

**Error 409 — duplicate name**
```json
{
  "message": "Category 'Vegetables' already exists",
  "errors": []
}
```

---

### GET /api/v1/catalog/categories/{category_id}

```bash
curl http://localhost:8000/api/v1/catalog/categories/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

**Response 200**
```json
{
  "data": {
    "entity_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Vegetables",
    "description": "Fresh and frozen vegetables",
    "parent_id": null,
    "created_at": "2025-07-25T10:00:00Z",
    "updated_at": "2025-07-25T10:00:00Z"
  }
}
```

**Error 404**
```json
{
  "message": "Category not found",
  "errors": []
}
```

---

### PATCH /api/v1/catalog/categories/{category_id}

Partial update — only include fields you want to change.

**Body**
```json
{
  "name": "Fresh Vegetables",
  "description": "Seasonal fresh vegetables"
}
```

```bash
curl -X PATCH http://localhost:8000/api/v1/catalog/categories/3fa85f64-5717-4562-b3fc-2c963f66afa6 \
  -H "Content-Type: application/json" \
  -d '{"description": "Seasonal fresh vegetables"}'
```

**Response 200** — same as GET response with updated fields.

---

### DELETE /api/v1/catalog/categories/{category_id}

Soft-deletes the category. Rejects if the category has sub-categories or ingredients.

```bash
curl -X DELETE http://localhost:8000/api/v1/catalog/categories/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

**Response 204** — no body.

**Error 400 — category in use**
```json
{
  "message": "Cannot delete category with sub-categories",
  "errors": []
}
```

---

## Units of Measure

### GET /api/v1/catalog/units/

**Query parameters**

| Parameter | Type | Values | Description |
|-----------|------|--------|-------------|
| `page` | int | — | Page number |
| `size` | int | — | Page size |
| `unit_type` | string | `weight`, `volume`, `unit`, `length` | Filter by type |

```bash
curl "http://localhost:8000/api/v1/catalog/units/?unit_type=weight"
```

**Response 200**
```json
{
  "data": {
    "items": [
      {
        "entity_id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Kilogram",
        "abbreviation": "kg",
        "unit_type": "weight",
        "base_unit_id": null,
        "conversion_factor": null,
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

### POST /api/v1/catalog/units/

**Full body**
```json
{
  "name": "Kilogram",
  "abbreviation": "kg",
  "unit_type": "weight",
  "base_unit_id": null,
  "conversion_factor": null
}
```

**Derived unit body** (gram derived from kilogram)
```json
{
  "name": "Gram",
  "abbreviation": "g",
  "unit_type": "weight",
  "base_unit_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversion_factor": "0.001"
}
```

**Minimal body**
```json
{
  "name": "Kilogram",
  "abbreviation": "kg",
  "unit_type": "weight"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/catalog/units/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Kilogram", "abbreviation": "kg", "unit_type": "weight"}'
```

**Response 201**
```json
{
  "data": {
    "entity_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Kilogram",
    "abbreviation": "kg",
    "unit_type": "weight",
    "base_unit_id": null,
    "conversion_factor": null,
    "created_at": "2025-07-25T10:00:00Z",
    "updated_at": "2025-07-25T10:00:00Z"
  }
}
```

**Error 409 — duplicate abbreviation**
```json
{
  "message": "Unit with abbreviation 'kg' already exists",
  "errors": []
}
```

---

### GET /api/v1/catalog/units/{unit_id}

```bash
curl http://localhost:8000/api/v1/catalog/units/550e8400-e29b-41d4-a716-446655440000
```

---

### PATCH /api/v1/catalog/units/{unit_id}

```bash
curl -X PATCH http://localhost:8000/api/v1/catalog/units/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"name": "Kilogramme"}'
```

---

### DELETE /api/v1/catalog/units/{unit_id}

```bash
curl -X DELETE http://localhost:8000/api/v1/catalog/units/550e8400-e29b-41d4-a716-446655440000
```

**Response 204** — no body.

---

## Ingredients

### GET /api/v1/catalog/ingredients/

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `size` | int | Page size |
| `name` | string | Case-insensitive substring match on name |
| `sku` | string | Case-insensitive substring match on SKU |
| `category_id` | UUID | Filter by category |
| `is_active` | bool | Filter by active status |

```bash
# Search by name
curl "http://localhost:8000/api/v1/catalog/ingredients/?name=tom"

# Active ingredients in a category
curl "http://localhost:8000/api/v1/catalog/ingredients/?category_id=3fa85f64-5717-4562-b3fc-2c963f66afa6&is_active=true"

# Search by SKU
curl "http://localhost:8000/api/v1/catalog/ingredients/?sku=VEG-"
```

**Response 200**
```json
{
  "data": {
    "items": [
      {
        "entity_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "sku": "VEG-001",
        "name": "Tomato",
        "description": "Fresh ripe tomatoes",
        "category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        "unit_of_measure_id": "550e8400-e29b-41d4-a716-446655440000",
        "reorder_point": "5.0000",
        "reorder_quantity": "20.0000",
        "cost_per_unit": "1.5000",
        "is_active": true,
        "allergen_info": null,
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

### POST /api/v1/catalog/ingredients/

**Full body**
```json
{
  "sku": "VEG-001",
  "name": "Tomato",
  "description": "Fresh ripe tomatoes",
  "category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "unit_of_measure_id": "550e8400-e29b-41d4-a716-446655440000",
  "reorder_point": "5.00",
  "reorder_quantity": "20.00",
  "cost_per_unit": "1.50",
  "is_active": true,
  "allergen_info": null
}
```

**Minimal body**
```json
{
  "sku": "VEG-001",
  "name": "Tomato",
  "category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "unit_of_measure_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

```bash
curl -X POST http://localhost:8000/api/v1/catalog/ingredients/ \
  -H "Content-Type: application/json" \
  -d '{
    "sku": "VEG-001",
    "name": "Tomato",
    "category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "unit_of_measure_id": "550e8400-e29b-41d4-a716-446655440000",
    "reorder_point": "5.00",
    "reorder_quantity": "20.00",
    "cost_per_unit": "1.50"
  }'
```

**Response 201**
```json
{
  "data": {
    "entity_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "sku": "VEG-001",
    "name": "Tomato",
    "description": null,
    "category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "unit_of_measure_id": "550e8400-e29b-41d4-a716-446655440000",
    "reorder_point": "5.0000",
    "reorder_quantity": "20.0000",
    "cost_per_unit": "1.5000",
    "is_active": true,
    "allergen_info": null,
    "created_at": "2025-07-25T10:00:00Z",
    "updated_at": "2025-07-25T10:00:00Z"
  }
}
```

**Error 409 — duplicate SKU**
```json
{
  "message": "SKU 'VEG-001' already exists",
  "errors": []
}
```

**Error 404 — category not found**
```json
{
  "message": "Category not found",
  "errors": []
}
```

---

### GET /api/v1/catalog/ingredients/{ingredient_id}

Returns full detail including embedded category and unit of measure.

```bash
curl http://localhost:8000/api/v1/catalog/ingredients/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
```

**Response 200**
```json
{
  "data": {
    "entity_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "sku": "VEG-001",
    "name": "Tomato",
    "description": "Fresh ripe tomatoes",
    "category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "unit_of_measure_id": "550e8400-e29b-41d4-a716-446655440000",
    "reorder_point": "5.0000",
    "reorder_quantity": "20.0000",
    "cost_per_unit": "1.5000",
    "is_active": true,
    "allergen_info": null,
    "category": {
      "entity_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "name": "Vegetables",
      "description": "Fresh and frozen vegetables",
      "parent_id": null,
      "created_at": "2025-07-25T10:00:00Z",
      "updated_at": "2025-07-25T10:00:00Z"
    },
    "unit_of_measure": {
      "entity_id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Kilogram",
      "abbreviation": "kg",
      "unit_type": "weight",
      "base_unit_id": null,
      "conversion_factor": null,
      "created_at": "2025-07-25T10:00:00Z",
      "updated_at": "2025-07-25T10:00:00Z"
    },
    "created_at": "2025-07-25T10:00:00Z",
    "updated_at": "2025-07-25T10:00:00Z"
  }
}
```

---

### PATCH /api/v1/catalog/ingredients/{ingredient_id}

```bash
curl -X PATCH http://localhost:8000/api/v1/catalog/ingredients/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11 \
  -H "Content-Type: application/json" \
  -d '{"cost_per_unit": "1.75", "reorder_point": "8.00"}'
```

**Body** — all fields optional
```json
{
  "name": "Roma Tomato",
  "description": "Italian variety",
  "category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "unit_of_measure_id": "550e8400-e29b-41d4-a716-446655440000",
  "reorder_point": "8.00",
  "reorder_quantity": "25.00",
  "cost_per_unit": "1.75",
  "is_active": true,
  "allergen_info": null
}
```

**Response 200** — same as list response object (without nested category/UOM).

---

### DELETE /api/v1/catalog/ingredients/{ingredient_id}

```bash
curl -X DELETE http://localhost:8000/api/v1/catalog/ingredients/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11
```

**Response 204** — no body.

---

### GET /api/v1/catalog/ingredients/{ingredient_id}/suppliers

List all suppliers linked to this ingredient.

```bash
curl http://localhost:8000/api/v1/catalog/ingredients/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11/suppliers
```

**Response 200**
```json
{
  "data": [
    {
      "entity_id": "c1d2e3f4-0000-0000-0000-000000000001",
      "supplier_id": "b5c6d7e8-5717-4562-b3fc-2c963f66afa6",
      "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "supplier_sku": "TOM-RED-KG",
      "unit_cost": "1.20",
      "created_at": "2025-07-25T10:00:00Z",
      "updated_at": "2025-07-25T10:00:00Z"
    }
  ]
}
```

---

### POST /api/v1/catalog/ingredients/{ingredient_id}/suppliers/{supplier_id}

Link a supplier to an ingredient (or update the link if it already exists).

```bash
curl -X POST \
  "http://localhost:8000/api/v1/catalog/ingredients/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11/suppliers/b5c6d7e8-5717-4562-b3fc-2c963f66afa6" \
  -H "Content-Type: application/json" \
  -d '{"supplier_sku": "TOM-RED-KG", "unit_cost": "1.20"}'
```

**Full body**
```json
{
  "supplier_sku": "TOM-RED-KG",
  "unit_cost": "1.20"
}
```

**Minimal body** (no additional info)
```json
{}
```

**Response 201**
```json
{
  "data": {
    "entity_id": "c1d2e3f4-0000-0000-0000-000000000001",
    "supplier_id": "b5c6d7e8-5717-4562-b3fc-2c963f66afa6",
    "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
    "supplier_sku": "TOM-RED-KG",
    "unit_cost": "1.20",
    "created_at": "2025-07-25T10:00:00Z",
    "updated_at": "2025-07-25T10:00:00Z"
  }
}
```

---

## Suppliers

### GET /api/v1/catalog/suppliers/

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `size` | int | Page size |
| `name` | string | Case-insensitive substring match |
| `is_active` | bool | Filter by active status |

```bash
curl "http://localhost:8000/api/v1/catalog/suppliers/?name=fresh&is_active=true"
```

**Response 200**
```json
{
  "data": {
    "items": [
      {
        "entity_id": "b5c6d7e8-5717-4562-b3fc-2c963f66afa6",
        "name": "Fresh Farms Co.",
        "contact_name": "John Smith",
        "email": "orders@freshfarms.com",
        "phone": "+1-555-0100",
        "address": "123 Farm Road, Springfield",
        "tax_id": "US-123456789",
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

### POST /api/v1/catalog/suppliers/

**Full body**
```json
{
  "name": "Fresh Farms Co.",
  "contact_name": "John Smith",
  "email": "orders@freshfarms.com",
  "phone": "+1-555-0100",
  "address": "123 Farm Road, Springfield",
  "tax_id": "US-123456789",
  "is_active": true
}
```

**Minimal body**
```json
{
  "name": "Fresh Farms Co."
}
```

```bash
curl -X POST http://localhost:8000/api/v1/catalog/suppliers/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Fresh Farms Co.",
    "contact_name": "John Smith",
    "email": "orders@freshfarms.com",
    "phone": "+1-555-0100"
  }'
```

**Response 201**
```json
{
  "data": {
    "entity_id": "b5c6d7e8-5717-4562-b3fc-2c963f66afa6",
    "name": "Fresh Farms Co.",
    "contact_name": "John Smith",
    "email": "orders@freshfarms.com",
    "phone": "+1-555-0100",
    "address": null,
    "tax_id": null,
    "is_active": true,
    "created_at": "2025-07-25T10:00:00Z",
    "updated_at": "2025-07-25T10:00:00Z"
  }
}
```

---

### GET /api/v1/catalog/suppliers/{supplier_id}

```bash
curl http://localhost:8000/api/v1/catalog/suppliers/b5c6d7e8-5717-4562-b3fc-2c963f66afa6
```

---

### PATCH /api/v1/catalog/suppliers/{supplier_id}

```bash
curl -X PATCH http://localhost:8000/api/v1/catalog/suppliers/b5c6d7e8-5717-4562-b3fc-2c963f66afa6 \
  -H "Content-Type: application/json" \
  -d '{"phone": "+1-555-0199", "is_active": false}'
```

**Body** — all fields optional
```json
{
  "name": "Fresh Farms Co. (Updated)",
  "contact_name": "Jane Smith",
  "email": "neworders@freshfarms.com",
  "phone": "+1-555-0199",
  "address": "456 New Farm Road",
  "tax_id": "US-987654321",
  "is_active": false
}
```

---

### DELETE /api/v1/catalog/suppliers/{supplier_id}

```bash
curl -X DELETE http://localhost:8000/api/v1/catalog/suppliers/b5c6d7e8-5717-4562-b3fc-2c963f66afa6
```

**Response 204** — no body.

---

### GET /api/v1/catalog/suppliers/{supplier_id}/ingredients

List all ingredients linked to this supplier.

```bash
curl http://localhost:8000/api/v1/catalog/suppliers/b5c6d7e8-5717-4562-b3fc-2c963f66afa6/ingredients
```

**Response 200**
```json
{
  "data": [
    {
      "entity_id": "c1d2e3f4-0000-0000-0000-000000000001",
      "supplier_id": "b5c6d7e8-5717-4562-b3fc-2c963f66afa6",
      "ingredient_id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
      "supplier_sku": "TOM-RED-KG",
      "unit_cost": "1.20",
      "created_at": "2025-07-25T10:00:00Z",
      "updated_at": "2025-07-25T10:00:00Z"
    }
  ]
}
```

---

### POST /api/v1/catalog/suppliers/{supplier_id}/ingredients/{ingredient_id}

Link an ingredient to a supplier (or update if the link already exists).

```bash
curl -X POST \
  "http://localhost:8000/api/v1/catalog/suppliers/b5c6d7e8-5717-4562-b3fc-2c963f66afa6/ingredients/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11" \
  -H "Content-Type: application/json" \
  -d '{"supplier_sku": "TOM-RED-KG", "unit_cost": "1.20"}'
```

**Response 201** — same as ingredient/suppliers link response.

---

### DELETE /api/v1/catalog/suppliers/{supplier_id}/ingredients/{ingredient_id}

Remove a supplier-ingredient link.

```bash
curl -X DELETE \
  "http://localhost:8000/api/v1/catalog/suppliers/b5c6d7e8-5717-4562-b3fc-2c963f66afa6/ingredients/a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
```

**Response 204** — no body.

**Error 404**
```json
{
  "message": "Supplier-ingredient link not found",
  "errors": []
}
```

---

## Error Reference

| HTTP Status | `error_code` | When it happens |
|-------------|--------------|-----------------|
| 400 | `category_in_use` | Deleting a category that has sub-categories or ingredients |
| 400 | `ingredient_in_use` | Deleting an ingredient referenced by stock (future) |
| 404 | `not_found` | Resource not found by ID |
| 409 | `duplicate_sku` | Creating an ingredient with an already-existing SKU |
| 409 | `conflict` | Creating a category/unit with a duplicate name or abbreviation |
| 422 | `unprocessable_entity` | Pydantic validation failed (missing required field, wrong type, etc.) |

**Validation error example (422)**
```json
{
  "message": "Validation error",
  "errors": [
    {
      "field": "name",
      "message": "String should have at least 1 character"
    },
    {
      "field": "unit_type",
      "message": "Input should be 'weight', 'volume', 'unit' or 'length'"
    }
  ]
}
```

---

## End-to-end Test Sequence

Run these in order to test the full catalog workflow:

```bash
BASE="http://localhost:8000/api/v1/catalog"

# 1. Create a unit of measure
KG=$(curl -s -X POST $BASE/units/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Kilogram","abbreviation":"kg","unit_type":"weight"}')
KG_ID=$(echo $KG | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['entity_id'])")
echo "Unit created: $KG_ID"

# 2. Create a category
CAT=$(curl -s -X POST $BASE/categories/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Vegetables","description":"Fresh vegetables"}')
CAT_ID=$(echo $CAT | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['entity_id'])")
echo "Category created: $CAT_ID"

# 3. Create an ingredient
ING=$(curl -s -X POST $BASE/ingredients/ \
  -H "Content-Type: application/json" \
  -d "{\"sku\":\"VEG-001\",\"name\":\"Tomato\",\"category_id\":\"$CAT_ID\",\"unit_of_measure_id\":\"$KG_ID\",\"reorder_point\":\"5\",\"cost_per_unit\":\"1.50\"}")
ING_ID=$(echo $ING | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['entity_id'])")
echo "Ingredient created: $ING_ID"

# 4. Create a supplier
SUP=$(curl -s -X POST $BASE/suppliers/ \
  -H "Content-Type: application/json" \
  -d '{"name":"Fresh Farms Co.","email":"orders@freshfarms.com"}')
SUP_ID=$(echo $SUP | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['entity_id'])")
echo "Supplier created: $SUP_ID"

# 5. Link supplier to ingredient
curl -s -X POST "$BASE/ingredients/$ING_ID/suppliers/$SUP_ID" \
  -H "Content-Type: application/json" \
  -d '{"supplier_sku":"TOM-001","unit_cost":"1.20"}' | python3 -m json.tool

# 6. Verify ingredient detail (includes category + UOM)
curl -s "$BASE/ingredients/$ING_ID" | python3 -m json.tool

# 7. Search ingredients
curl -s "$BASE/ingredients/?name=tom" | python3 -m json.tool
```
