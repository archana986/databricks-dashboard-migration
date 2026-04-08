"""
Genie Space Benchmarks

Functions for extracting and exporting benchmark questions.
"""

import csv
import json
import os
from dataclasses import dataclass, asdict
from typing import List, Optional


@dataclass
class Benchmark:
    """A single benchmark question for a Genie Space."""
    space_id: str
    space_title: str
    question_id: str
    question: str
    sql_answer: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


def extract_benchmarks(
    serialized_space: str,
    space_id: str = "",
    space_title: str = ""
) -> List[Benchmark]:
    """
    Parse benchmarks from serialized_space JSON.

    Args:
        serialized_space: The serialized_space JSON string
        space_id: The Genie Space ID (for reference)
        space_title: The Genie Space title (for reference)

    Returns:
        List of Benchmark objects
    """
    benchmarks = []

    if not serialized_space:
        return benchmarks

    try:
        data = json.loads(serialized_space)
    except json.JSONDecodeError:
        return benchmarks

    benchmark_data = data.get("benchmarks", [])

    for bm in benchmark_data:
        question_id = bm.get("id", "")
        question_text = ""
        sql_answer = None

        questions = bm.get("question", [])
        if isinstance(questions, list) and questions:
            question_text = questions[0]
        elif isinstance(questions, str):
            question_text = questions

        sql_answer = bm.get("sql_answer") or bm.get("expected_sql") or bm.get("gold_sql")

        if question_text:
            benchmarks.append(Benchmark(
                space_id=space_id,
                space_title=space_title,
                question_id=question_id,
                question=question_text,
                sql_answer=sql_answer
            ))

    return benchmarks


def export_benchmarks_json(
    benchmarks: List[Benchmark],
    output_path: str
) -> None:
    """
    Write benchmarks to a JSON file.

    Args:
        benchmarks: List of Benchmark objects
        output_path: Path to write the JSON file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    data = [b.to_dict() for b in benchmarks]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def export_benchmarks_csv(
    benchmarks: List[Benchmark],
    output_path: str
) -> None:
    """
    Write benchmarks to a CSV file.

    Args:
        benchmarks: List of Benchmark objects
        output_path: Path to write the CSV file
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fieldnames = ["space_id", "space_title", "question_id", "question", "sql_answer"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for b in benchmarks:
            writer.writerow(b.to_dict())


def export_all_benchmarks(
    spaces: List[dict],
    volume_path: str
) -> str:
    """
    Export benchmarks for all spaces to the volume.

    Args:
        spaces: List of exported space dictionaries with serialized_space
        volume_path: Base path to the UC volume

    Returns:
        Path to the consolidated benchmarks CSV
    """
    all_benchmarks = []
    benchmarks_dir = os.path.join(volume_path, "benchmarks")
    os.makedirs(benchmarks_dir, exist_ok=True)

    for space in spaces:
        space_id = space.get("_metadata", {}).get("source_space_id", "")
        title = space.get("title", "")
        serialized_space = space.get("serialized_space", "")

        if not serialized_space:
            continue

        bms = extract_benchmarks(serialized_space, space_id, title)
        all_benchmarks.extend(bms)

        if bms:
            safe_title = title.lower().replace(" ", "_")[:50]
            json_path = os.path.join(benchmarks_dir, f"{safe_title}_benchmarks.json")
            export_benchmarks_json(bms, json_path)

    csv_path = os.path.join(benchmarks_dir, "all_benchmarks.csv")
    export_benchmarks_csv(all_benchmarks, csv_path)

    print(f"Exported {len(all_benchmarks)} benchmark questions to {csv_path}")
    return csv_path


def count_benchmarks(serialized_space: str) -> int:
    """
    Count the number of benchmarks in a serialized_space.

    Args:
        serialized_space: The serialized_space JSON string

    Returns:
        Number of benchmark questions
    """
    if not serialized_space:
        return 0

    try:
        data = json.loads(serialized_space)
        return len(data.get("benchmarks", []))
    except json.JSONDecodeError:
        return 0
