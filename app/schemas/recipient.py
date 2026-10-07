from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class RecipientInput(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Jane Doe",
                "email": "jane.doe@example.com",
                "metadata": {"grade": "A+", "role": "Full Stack Developer"},
            }
        }
    )

    name: str = Field(..., description="Recipient full name")
    email: Optional[str] = Field(None, description="Recipient email address")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional custom key-value attributes")
