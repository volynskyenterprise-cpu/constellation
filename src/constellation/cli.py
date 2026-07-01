from __future__ import annotations

import argparse
from pathlib import Path

from .kernel import ConstellationKernel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m constellation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a workflow until completion or approval gate.")
    run_parser.add_argument("workflow", type=Path, help="Path to workflow YAML file.")
    run_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")

    args = parser.parse_args(argv)
    if args.command == "run":
        kernel = ConstellationKernel(args.root.resolve())
        result = kernel.run_workflow(args.workflow)
        print(f"workflow_run_id: {result.workflow_run_id}")
        print(f"workflow_id: {result.workflow_id}")
        print(f"status: {result.status}")
        print(f"message_log: {result.message_log}")
        print(f"event_log: {result.event_log}")
        print(f"working_memory: {result.working_memory}")
        if result.approval_path:
            print(f"approval_required: {result.approval_path}")
        return 0
    return 2
