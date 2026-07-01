from __future__ import annotations

import argparse
from pathlib import Path

from .kernel import ConstellationKernel
from .state import WorkflowStateError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m constellation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a workflow until completion or approval gate.")
    run_parser.add_argument("workflow", type=Path, help="Path to workflow YAML file.")
    run_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")

    approvals_parser = subparsers.add_parser("approvals", help="Manage approval records.")
    approvals_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    approvals_subparsers = approvals_parser.add_subparsers(dest="approvals_command", required=True)
    approvals_subparsers.add_parser("list", help="List pending approvals.")
    approve_parser = approvals_subparsers.add_parser("approve", help="Explicitly approve a pending approval.")
    approve_parser.add_argument("approval_id", help="Actual approval ID from the pending approval record.")

    resume_parser = subparsers.add_parser("resume", help="Resume a workflow run after approval.")
    resume_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    resume_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")

    runs_parser = subparsers.add_parser("runs", help="Inspect workflow runs.")
    runs_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    runs_subparsers = runs_parser.add_subparsers(dest="runs_command", required=True)
    runs_subparsers.add_parser("list", help="List known workflow runs.")
    show_parser = runs_subparsers.add_parser("show", help="Show one workflow run.")
    show_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")

    args = parser.parse_args(argv)
    if args.command == "run":
        kernel = ConstellationKernel(args.root.resolve())
        result = kernel.run_workflow(args.workflow)
        _print_result(result)
        return 0
    if args.command == "approvals":
        kernel = ConstellationKernel(args.root.resolve())
        if args.approvals_command == "list":
            approvals = kernel.list_pending_approvals()
            if not approvals:
                print("No pending approvals.")
                return 0
            for approval in approvals:
                print(
                    f"{approval['id']} workflow_run_id={approval['workflow_run_id']} "
                    f"workflow_id={approval['workflow_id']} gate={approval['gate_id']} "
                    f"status={approval['status']}"
                )
            return 0
        if args.approvals_command == "approve":
            approval = kernel.approve(args.approval_id)
            print(f"approval_id: {approval['id']}")
            print(f"workflow_run_id: {approval['workflow_run_id']}")
            print(f"status: {approval['status']}")
            return 0
    if args.command == "resume":
        kernel = ConstellationKernel(args.root.resolve())
        try:
            result = kernel.resume_workflow(args.workflow_run_id)
        except WorkflowStateError as exc:
            print(f"error: {exc}")
            return 1
        _print_result(result)
        return 0
    if args.command == "runs":
        kernel = ConstellationKernel(args.root.resolve())
        if args.runs_command == "list":
            runs = kernel.list_runs()
            if not runs:
                print("No workflow runs found.")
                return 0
            for run in runs:
                print(
                    f"{run.workflow_run_id} workflow_id={run.workflow_id} status={run.status} "
                    f"current_step={run.current_step} created_at={run.created_at} updated_at={run.updated_at}"
                )
            return 0
        if args.runs_command == "show":
            try:
                details = kernel.show_run(args.workflow_run_id)
            except WorkflowStateError as exc:
                print(f"error: {exc}")
                return 1
            _print_run_details(details)
            return 0
    return 2


def _print_result(result) -> None:
    print(f"workflow_run_id: {result.workflow_run_id}")
    print(f"workflow_id: {result.workflow_id}")
    print(f"status: {result.status}")
    print(f"message_log: {result.message_log}")
    print(f"event_log: {result.event_log}")
    print(f"working_memory: {result.working_memory}")
    if result.approval_path:
        print(f"approval_required: {result.approval_path}")


def _print_run_details(details) -> None:
    summary = details.summary
    print(f"workflow_run_id: {summary.workflow_run_id}")
    print(f"workflow_id: {summary.workflow_id}")
    print(f"status: {summary.status}")
    print(f"current_step: {summary.current_step}")
    print(f"created_at: {summary.created_at}")
    print(f"updated_at: {summary.updated_at}")
    print(f"approval_status: {details.approval_status}")
    print(f"message_log: {details.message_log_path}")
    print(f"event_log: {details.event_log_path}")
    print(f"working_memory: {details.working_memory_path}")
    print("recent_events:")
    for event in details.recent_events:
        print(f"  {event.get('timestamp', 'unknown')} {event.get('type', 'unknown')} {event.get('summary', '')}")
    print("recent_messages:")
    for message in details.recent_messages:
        receiver = message.get("receiver", {})
        receiver_name = receiver.get("name", "unknown") if isinstance(receiver, dict) else "unknown"
        print(
            f"  {message.get('timestamp', 'unknown')} {message.get('requested_action', 'unknown')} "
            f"receiver={receiver_name} status={message.get('status', 'unknown')}"
        )
