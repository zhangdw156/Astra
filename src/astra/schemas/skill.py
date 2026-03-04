"""
Skill schema — Anthropic-style tool definitions for the Astra registry.

Skills represent standardized tool definitions that can be collected,
validated, and used to construct mission blueprints and execution traces.
"""

from typing import Any

from pydantic import BaseModel, Field


class Skill(BaseModel):
    """
    A standardized tool definition in Anthropic style.

    Maps to the Claude API tool format:
    - name: Tool identifier (^[a-zA-Z0-9_-]{1,64}$)
    - description: Plaintext description of behavior and usage
    - input_schema: JSON Schema for expected parameters
    """

    name: str = Field(..., description="Tool name; must match ^[a-zA-Z0-9_-]{1,64}$")
    description: str = Field(..., description="Plaintext description of the tool")
    input_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema defining expected input parameters",
    )
