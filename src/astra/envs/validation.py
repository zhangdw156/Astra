from __future__ import annotations

from typing import Any


def compare_state(
    actual: Any,
    expected: Any,
    *,
    path: str = "$",
    subset: bool = True,
) -> list[dict[str, Any]]:
    diffs: list[dict[str, Any]] = []

    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [
                {
                    "path": path,
                    "kind": "type_mismatch",
                    "expected_type": "dict",
                    "actual_type": type(actual).__name__,
                }
            ]

        for key, expected_value in expected.items():
            if key not in actual:
                diffs.append({"path": f"{path}.{key}", "kind": "missing_key"})
                continue
            diffs.extend(
                compare_state(
                    actual[key],
                    expected_value,
                    path=f"{path}.{key}",
                    subset=subset,
                )
            )

        if not subset:
            for key in actual:
                if key not in expected:
                    diffs.append({"path": f"{path}.{key}", "kind": "unexpected_key"})
        return diffs

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return [
                {
                    "path": path,
                    "kind": "type_mismatch",
                    "expected_type": "list",
                    "actual_type": type(actual).__name__,
                }
            ]

        if subset and len(actual) < len(expected):
            return [
                {
                    "path": path,
                    "kind": "list_too_short",
                    "expected_length": len(expected),
                    "actual_length": len(actual),
                }
            ]

        if not subset and len(actual) != len(expected):
            diffs.append(
                {
                    "path": path,
                    "kind": "length_mismatch",
                    "expected_length": len(expected),
                    "actual_length": len(actual),
                }
            )

        for index, expected_item in enumerate(expected):
            if index >= len(actual):
                break
            diffs.extend(
                compare_state(
                    actual[index],
                    expected_item,
                    path=f"{path}[{index}]",
                    subset=subset,
                )
            )
        return diffs

    if actual != expected:
        diffs.append(
            {
                "path": path,
                "kind": "value_mismatch",
                "expected": expected,
                "actual": actual,
            }
        )
    return diffs


def is_state_match(actual: Any, expected: Any, *, subset: bool = True) -> bool:
    return not compare_state(actual, expected, subset=subset)
