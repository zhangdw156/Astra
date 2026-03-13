from __future__ import annotations

from typing import Any

from .types import EnvironmentProfile


def validate_hybrid_result(
    *,
    profile: EnvironmentProfile,
    result: dict[str, Any],
) -> None:
    if profile.backend_mode != "hybrid":
        return

    if profile.state_mutation_policy != "programmatic":
        raise ValueError(
            "Hybrid backend profiles must declare state_mutation_policy=programmatic"
        )

    generated_fields = set(profile.generated_result_fields)
    if not generated_fields:
        return

    for field_name, value in result.items():
        if field_name not in generated_fields:
            continue
        if not isinstance(value, str):
            raise ValueError(
                f"Hybrid generated field must be string-like text: {field_name}"
            )
