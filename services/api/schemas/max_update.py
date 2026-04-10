"""Module for services/api/schemas/max update."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MaxUpdate(BaseModel):
  """Represent maxupdate."""
  update_id: Optional[str] = None
  event_id: Optional[str] = None
  update_type: Optional[str] = None
  payload: Dict[str, Any] = Field(default_factory=dict)
