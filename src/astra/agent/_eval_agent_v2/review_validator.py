from __future__ import annotations

from typing import Any


class EvalReviewValidator:
    REQUIRED_FIELDS = {
        "summary",
        "strongest_positive",
        "strongest_negative",
        "root_causes",
        "should_repair",
        "repair_target",
        "repair_strategy",
        "export_training_artifact",
    }

    ALLOWED_REPAIR_TARGETS = {"none", "blueprint", "trajectory", "both"}

    @classmethod
    def normalize(cls, data: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(data)
        root_causes = normalized.get("root_causes")
        if isinstance(root_causes, str):
            normalized["root_causes"] = [root_causes]
        elif isinstance(root_causes, list):
            normalized["root_causes"] = [
                str(item).strip() for item in root_causes if str(item).strip()
            ]
        if normalized.get("repair_target") in ("", None):
            normalized["repair_target"] = "none"
        if "should_repair" not in normalized:
            normalized["should_repair"] = False
        if "export_training_artifact" not in normalized:
            normalized["export_training_artifact"] = False
        return normalized

    @classmethod
    def validate(cls, data: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for field in cls.REQUIRED_FIELDS:
            if field not in data:
                errors.append(f"缺少 review 字段: {field}")

        if "summary" in data and (
            not isinstance(data["summary"], str) or not data["summary"].strip()
        ):
            errors.append("summary 必须为非空字符串")
        if "strongest_positive" in data and (
            not isinstance(data["strongest_positive"], str)
            or not data["strongest_positive"].strip()
        ):
            errors.append("strongest_positive 必须为非空字符串")
        if "strongest_negative" in data and (
            not isinstance(data["strongest_negative"], str)
            or not data["strongest_negative"].strip()
        ):
            errors.append("strongest_negative 必须为非空字符串")
        root_causes = data.get("root_causes")
        if not isinstance(root_causes, list) or not root_causes or not all(
            isinstance(item, str) and item.strip() for item in root_causes
        ):
            errors.append("root_causes 必须为非空字符串数组")
        if "should_repair" in data and not isinstance(data["should_repair"], bool):
            errors.append("should_repair 必须为布尔值")
        repair_target = data.get("repair_target")
        if repair_target not in cls.ALLOWED_REPAIR_TARGETS:
            errors.append(
                "repair_target 必须为 "
                f"{sorted(cls.ALLOWED_REPAIR_TARGETS)}"
            )
        if "repair_strategy" in data and not isinstance(data["repair_strategy"], str):
            errors.append("repair_strategy 必须为字符串")
        if "export_training_artifact" in data and not isinstance(
            data["export_training_artifact"], bool
        ):
            errors.append("export_training_artifact 必须为布尔值")
        return errors
