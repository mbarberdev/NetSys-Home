"""Pydantic request/response models for the NetSys-Home API."""

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


Action = Literal["block", "isolate", "guest_network", "schedule_block"]


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1, max_length=32)
    mac: str = ""

    @field_validator("mac")
    @classmethod
    def normalize_mac(cls, v: str) -> str:
        return v.strip().upper()


class Device(BaseModel):
    id: int
    name: str
    type: str
    mac: str = ""
    ip: Optional[str] = None


class IntentRequest(BaseModel):
    device_id: int
    action: Optional[Action] = None
    text: Optional[str] = None
    time: Optional[str] = None

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @field_validator("time")
    @classmethod
    def strip_time(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v


class Classification(BaseModel):
    predicted_action: Action
    confidence: Optional[float] = None
    model: Optional[str] = None


class Policy(BaseModel):
    id: int
    type: str
    rule: str
    device_id: int
    action: str
    created_at: str


class IntentResponse(Policy):
    enforced: bool
    classification: Optional[Classification] = None


class ClassifyRequest(BaseModel):
    text: str = Field(min_length=1)


class ClassifyResponse(Classification):
    text: str


class StatusResponse(BaseModel):
    openwrt: str
    version: Optional[str] = None
    hostname: Optional[str] = None
    model: Optional[str] = None
    app_version: str
    classifier: str
