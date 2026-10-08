from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RecipientInput(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Recipient name cannot be blank")

        return value


class GenerationJobCreate(BaseModel):
    event_name: str = Field(min_length=1, max_length=200)
    certificate_title: str = Field(
        default="Certificate of Participation",
        min_length=1,
        max_length=200,
    )
    recipients: list[RecipientInput] = Field(min_length=1, max_length=5000)

    @field_validator("event_name", "certificate_title")
    @classmethod
    def validate_text_fields(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Field cannot be blank")

        return value


class RecipientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str | None
    status: str
    certificate_url: str | None = None
    error_message: str | None = None


class JobResponse(BaseModel):
    id: str
    event_name: str
    certificate_title: str
    total_recipients: int
    successful_count: int
    failed_count: int
    status: str
    created_at: datetime
    updated_at: datetime
    progress_percent: float
    recipients: list[RecipientResponse]