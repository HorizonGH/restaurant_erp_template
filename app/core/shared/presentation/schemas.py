from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BaseInputSchema(BaseSchema):
    pass


class BaseOutputSchema(BaseSchema):
    entity_id: UUID
    created_at: datetime
    updated_at: datetime
