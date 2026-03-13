#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def load_pipeline2_module():
    module_path = Path(__file__).resolve().parent / "pipeline2_program_backend_smoke.py"
    spec = importlib.util.spec_from_file_location("pipeline2_program_backend_smoke", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load pipeline module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_persona_lines(path: Path | None) -> list[str]:
    if path is None:
        return ["Program backend batch persona"]

    if not path.exists():
        raise FileNotFoundError(f"persona file not found: {path}")

    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    lines = [line for line in lines if line]
    return lines or ["Program backend batch persona"]


def select_personas_for_skill(
    *,
    persona_lines: list[str],
    count_per_skill: int,
    shuffle_personas: bool,
    seed: int,
    skill_name: str,
) -> list[str]:
    rng = random.Random(f"{seed}:{skill_name}")
    selected = list(persona_lines)
    if shuffle_personas:
        rng.shuffle(selected)

    if count_per_skill <= len(selected):
        return selected[:count_per_skill]

    extra = count_per_skill - len(selected)
    selected.extend(rng.choices(persona_lines, k=extra))
    return selected


def write_skill_summary(*, skill_output_root: Path, samples: list[dict[str, Any]]) -> None:
    sample_records = [
        {
            "sample_index": item["sample_index"],
            "run_id": item["run_id"],
            "accepted": item["accepted"],
            "error": item["error"],
        }
        for item in samples
    ]
    summary = {
        "total_count": len(samples),
        "succeeded_count": sum(1 for item in samples if item["accepted"]),
        "failed_count": sum(1 for item in samples if not item["accepted"]),
        "accepted_count": sum(1 for item in samples if item["accepted"]),
        "rejected_count": sum(1 for item in samples if not item["accepted"]),
        "samples": sample_records,
    }
    (skill_output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    manifest_lines = [
        json.dumps(
            {
                "sample_index": item["sample_index"],
                "run_id": item["run_id"],
                "skill_name": item["skill_name"],
                "accepted": item["accepted"],
                "error": item["error"],
                "score": item["score"],
            },
            ensure_ascii=False,
        )
        for item in samples
    ]
    (skill_output_root / "manifest.jsonl").write_text(
        "\n".join(manifest_lines) + ("\n" if manifest_lines else ""),
        encoding="utf-8",
    )


def run_one_skill(
    *,
    pipeline2,
    skill_dir: Path,
    output_root: Path,
    persona_lines: list[str],
    count_per_skill: int,
    shuffle_personas: bool,
    seed: int,
) -> tuple[str, int, int]:
    skill_name = skill_dir.name
    selected_personas = select_personas_for_skill(
        persona_lines=persona_lines,
        count_per_skill=count_per_skill,
        shuffle_personas=shuffle_personas,
        seed=seed,
        skill_name=skill_name,
    )

    skill_output_root = output_root / skill_name
    samples: list[dict[str, Any]] = []

    for sample_index, persona_text in enumerate(selected_personas):
        try:
            result = pipeline2.synthesize_one(
                skill_dir=skill_dir,
                persona_text=persona_text,
                sample_index=sample_index,
                output_root=output_root,
            )
            samples.append(
                {
                    "sample_index": sample_index,
                    "run_id": result["trajectory"].run_id,
                    "skill_name": skill_name,
                    "accepted": True,
                    "error": "",
                    "score": result["evaluation"].score,
                }
            )
        except Exception as exc:
            samples.append(
                {
                    "sample_index": sample_index,
                    "run_id": f"{skill_name}-sample-{sample_index:03d}",
                    "skill_name": skill_name,
                    "accepted": False,
                    "error": str(exc),
                    "score": 0.0,
                }
            )

    write_skill_summary(skill_output_root=skill_output_root, samples=samples)
    succeeded = sum(1 for item in samples if item["accepted"])
    failed = len(samples) - succeeded
    return skill_name, succeeded, failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Program-backend batch synthesis pipeline")
    parser.add_argument("--selected-skills", type=Path)
    parser.add_argument("--skills-root", type=Path, required=True)
    parser.add_argument("--persona-path", type=Path)
    parser.add_argument("--count-per-skill", type=int, default=50)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--limit-skills", type=int, default=0)
    parser.add_argument("--shuffle-personas", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    pipeline2 = load_pipeline2_module()
    skills_root = args.skills_root.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    if args.selected_skills:
        skill_names = pipeline2.load_selected_skills(args.selected_skills.resolve())
    else:
        skill_names = pipeline2.discover_skills(skills_root)

    if args.limit_skills > 0:
        skill_names = skill_names[: args.limit_skills]

    persona_lines = load_persona_lines(args.persona_path.resolve() if args.persona_path else None)

    print("=" * 60)
    print("Pipeline3 (program backend batch)")
    print("=" * 60)
    print(f"Skills root:          {skills_root}")
    print(f"Output root:          {output_root}")
    print(f"Selected skill count: {len(skill_names)}")
    print(f"Count per skill:      {args.count_per_skill}")
    print(f"Max workers:          {args.max_workers}")
    print(f"Shuffle personas:     {args.shuffle_personas}")
    print(f"Seed:                 {args.seed}")
    print("=" * 60)

    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_map = {
            executor.submit(
                run_one_skill,
                pipeline2=pipeline2,
                skill_dir=skills_root / skill_name,
                output_root=output_root,
                persona_lines=persona_lines,
                count_per_skill=args.count_per_skill,
                shuffle_personas=args.shuffle_personas,
                seed=args.seed,
            ): skill_name
            for skill_name in skill_names
        }

        for future in as_completed(future_map):
            skill_name = future_map[future]
            try:
                _, succeeded, failed = future.result()
                results.append(
                    {
                        "skill_name": skill_name,
                        "accepted": failed == 0,
                        "succeeded_count": succeeded,
                        "failed_count": failed,
                    }
                )
                print(
                    f"[OK] {skill_name} | succeeded_samples={succeeded} | failed_samples={failed}"
                )
            except Exception as exc:
                failures.append({"skill_name": skill_name, "error": str(exc)})
                print(f"[FAIL] {skill_name}: {exc}")

    summary = {
        "total_skills": len(skill_names),
        "count_per_skill": args.count_per_skill,
        "requested_samples": len(skill_names) * args.count_per_skill,
        "succeeded_skills": sum(1 for item in results if item["accepted"]),
        "failed_skills": len(failures),
        "succeeded_samples": sum(item["succeeded_count"] for item in results),
        "failed_samples": sum(item["failed_count"] for item in results),
        "failures": failures,
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_root / "manifest.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in results) + ("\n" if results else ""),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("Completed")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("=" * 60)

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
