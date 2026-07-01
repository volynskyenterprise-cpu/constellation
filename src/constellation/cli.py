from __future__ import annotations

import argparse
import json
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
    archive_parser = runs_subparsers.add_parser("archive", help="Archive one workflow run.")
    archive_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    delete_parser = runs_subparsers.add_parser("delete", help="Delete one workflow run after confirmation.")
    delete_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    delete_parser.add_argument("--yes", action="store_true", help="Confirm deletion without prompting.")
    prune_parser = runs_subparsers.add_parser("prune", help="Archive or delete old workflow runs.")
    prune_parser.add_argument("--older-than", type=int, required=True, help="Age threshold in days.")
    prune_parser.add_argument("--delete", action="store_true", help="Delete instead of archiving old runs.")
    prune_parser.add_argument("--yes", action="store_true", help="Confirm prune deletion without prompting.")

    providers_parser = subparsers.add_parser("providers", help="Inspect configured model providers.")
    providers_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    providers_subparsers = providers_parser.add_subparsers(dest="providers_command", required=True)
    providers_subparsers.add_parser("list", help="List configured providers.")
    provider_show_parser = providers_subparsers.add_parser("show", help="Show one provider.")
    provider_show_parser.add_argument("provider_name", help="Provider name from config/providers.yaml.")
    providers_subparsers.add_parser("health", help="Check provider health.")

    context_parser = subparsers.add_parser("context", help="Inspect assembled execution context.")
    context_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    context_subparsers = context_parser.add_subparsers(dest="context_command", required=True)
    context_show_parser = context_subparsers.add_parser("show", help="Show assembled context for a run.")
    context_show_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")

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
        if args.runs_command == "archive":
            try:
                result = kernel.archive_run(args.workflow_run_id)
            except WorkflowStateError as exc:
                print(f"error: {exc}")
                return 1
            _print_lifecycle_result(result)
            return 0
        if args.runs_command == "delete":
            if not args.yes and not _confirm_delete(args.workflow_run_id):
                print("delete_aborted")
                return 1
            try:
                result = kernel.delete_run(args.workflow_run_id)
            except WorkflowStateError as exc:
                print(f"error: {exc}")
                return 1
            _print_lifecycle_result(result)
            return 0
        if args.runs_command == "prune":
            action = "delete" if args.delete else "archive"
            if action == "delete" and not args.yes and not _confirm_delete(f"runs older than {args.older_than} days"):
                print("prune_aborted")
                return 1
            try:
                results = kernel.prune_runs(args.older_than, action)
            except ValueError as exc:
                print(f"error: {exc}")
                return 1
            print(f"pruned_count: {len(results)}")
            for result in results:
                _print_lifecycle_result(result)
            return 0
    if args.command == "providers":
        kernel = ConstellationKernel(args.root.resolve())
        if args.providers_command == "list":
            for provider in kernel.list_providers():
                print(
                    f"{provider.id} enabled={provider.enabled} type={provider.provider_type} "
                    f"model={provider.model} capabilities={','.join(provider.capabilities)}"
                )
            return 0
        if args.providers_command == "show":
            try:
                provider = kernel.show_provider(args.provider_name)
            except Exception as exc:
                print(f"error: {exc}")
                return 1
            print(f"name: {provider.id}")
            print(f"enabled: {provider.enabled}")
            print(f"type: {provider.provider_type}")
            print(f"model: {provider.model}")
            print(f"role: {provider.role}")
            print(f"capabilities: {','.join(provider.capabilities)}")
            return 0
        if args.providers_command == "health":
            for result in kernel.provider_health():
                print(
                    f"{result.get('provider_name')} status={result.get('status')} "
                    f"enabled={result.get('enabled')}"
                )
            return 0
    if args.command == "context":
        kernel = ConstellationKernel(args.root.resolve())
        if args.context_command == "show":
            try:
                context = kernel.show_context(args.workflow_run_id)
            except Exception as exc:
                print(f"error: {exc}")
                return 1
            print(json.dumps(context.to_dict(), indent=2, sort_keys=True))
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


def _print_lifecycle_result(result) -> None:
    print(f"workflow_run_id: {result.workflow_run_id}")
    print(f"action: {result.action}")
    print(f"status: {result.status}")
    if result.location:
        print(f"location: {result.location}")


def _confirm_delete(target: str) -> bool:
    response = input(f"Type DELETE to confirm deletion of {target}: ")
    return response == "DELETE"
