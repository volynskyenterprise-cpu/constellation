from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from constellation.cli import main
from constellation.evidence import EvidenceStore
from constellation.knowledge_graph import GraphEdge, GraphNode, KnowledgeGraph, KnowledgeGraphBuilder, KnowledgeGraphStore
from constellation.pkos import PKOSKnowledgeOrganization
from constellation.research import ResearchOrganization
from constellation.state import WorkflowStateError


ROOT = Path(__file__).resolve().parents[1]


class KnowledgeGraphTests(unittest.TestCase):
    def test_graph_node_creation(self) -> None:
        node = _node("node_concept_test", "concept", "Test Concept")

        self.assertEqual(node.node_type, "concept")
        self.assertEqual(node.label, "Test Concept")
        self.assertEqual(node.to_dict()["node_id"], "node_concept_test")

    def test_graph_edge_creation(self) -> None:
        edge = _edge("edge_test", "node_a", "node_b", "references")

        self.assertEqual(edge.relationship_type, "references")
        self.assertEqual(edge.source_node_id, "node_a")
        self.assertEqual(edge.to_dict()["edge_id"], "edge_test")

    def test_graph_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            graph = KnowledgeGraph()
            graph.add_node(_node("node_concept_test", "concept", "Test Concept"))
            graph.add_edge(_edge("edge_test", "node_concept_test", "node_evidence_test", "references"))

            store = KnowledgeGraphStore(root)
            store.save(graph)
            loaded = store.load()

            self.assertIn("node_concept_test", loaded.nodes)
            self.assertIn("edge_test", loaded.edges)

    def test_graph_build_from_research_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ResearchOrganization(temp_root).run(_write_research_input(temp_root))

            graph = KnowledgeGraphBuilder(temp_root).build_run(result.workflow_run_id)

            node_types = {node.node_type for node in graph.nodes.values()}
            self.assertIn("workflow", node_types)
            self.assertIn("evidence", node_types)
            self.assertIn("source", node_types)
            self.assertIn("artifact", node_types)

    def test_graph_build_from_pkos_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = PKOSKnowledgeOrganization(temp_root).ingest(_write_pkos_input(temp_root))

            graph = KnowledgeGraphBuilder(temp_root).build_run(result.workflow_run_id)

            labels = {node.label for node in graph.nodes.values()}
            self.assertIn("PKOS Concept", labels)
            self.assertIn("Traceability", labels)

    def test_deterministic_topic_extraction_from_markdown_headings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ResearchOrganization(temp_root).run(_write_research_input(temp_root))

            graph = KnowledgeGraphBuilder(temp_root).build_run(result.workflow_run_id)
            topics = graph.find_nodes(node_type="topic")

            self.assertTrue(any(node.label == "Research Topic" for node in topics))

    def test_deterministic_prefix_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ResearchOrganization(temp_root).run(_write_research_input(temp_root))

            graph = KnowledgeGraphBuilder(temp_root).build_run(result.workflow_run_id)
            node_types = {node.node_type for node in graph.nodes.values()}

            self.assertIn("concept", node_types)
            self.assertIn("risk", node_types)
            self.assertIn("assumption", node_types)
            self.assertIn("recommendation", node_types)

    def test_graph_cli_nodes_edges_show_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ResearchOrganization(temp_root).run(_write_research_input(temp_root))
            build_output = io.StringIO()
            with redirect_stdout(build_output):
                build_exit = main(["graph", "--root", str(temp_root), "build", result.workflow_run_id])
            graph = KnowledgeGraphStore(temp_root).load()
            node_id = next(iter(graph.nodes))
            nodes_output = io.StringIO()
            with redirect_stdout(nodes_output):
                nodes_exit = main(["graph", "--root", str(temp_root), "nodes"])
            edges_output = io.StringIO()
            with redirect_stdout(edges_output):
                edges_exit = main(["graph", "--root", str(temp_root), "edges"])
            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_exit = main(["graph", "--root", str(temp_root), "show", node_id])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["graph", "--root", str(temp_root), "export"])

            self.assertEqual(build_exit, 0)
            self.assertIn("nodes:", build_output.getvalue())
            self.assertEqual(nodes_exit, 0)
            self.assertIn("node_", nodes_output.getvalue())
            self.assertEqual(edges_exit, 0)
            self.assertIn("edge_", edges_output.getvalue())
            self.assertEqual(show_exit, 0)
            self.assertEqual(json.loads(show_output.getvalue())["node_id"], node_id)
            self.assertEqual(export_exit, 0)
            self.assertTrue((temp_root / "outputs" / "graph" / "knowledge-graph.md").exists())

    def test_idempotent_graph_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ResearchOrganization(temp_root).run(_write_research_input(temp_root))
            builder = KnowledgeGraphBuilder(temp_root)

            first = builder.build_run(result.workflow_run_id)
            second = builder.build_run(result.workflow_run_id)

            self.assertEqual(set(first.nodes), set(second.nodes))
            self.assertEqual(set(first.edges), set(second.edges))

    def test_missing_run_handling(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))

            with self.assertRaises(WorkflowStateError):
                KnowledgeGraphBuilder(temp_root).build_run("run_missing")

    def test_no_external_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            external = Path(temp_dir) / "external-vault"
            external.mkdir()
            sentinel = external / "note.md"
            sentinel.write_text("original", encoding="utf-8")
            result = PKOSKnowledgeOrganization(temp_root).ingest(_write_pkos_input(temp_root))

            KnowledgeGraphBuilder(temp_root).build_run(result.workflow_run_id)
            KnowledgeGraphStore(temp_root).export()

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "original")
            self.assertTrue((temp_root / "memory" / "graph" / "graph.json").exists())

    def test_workflow_artifact_and_evidence_edges_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(temp_root, invoke=True)
            result = ResearchOrganization(temp_root).run(_write_research_input(temp_root))

            graph = KnowledgeGraphBuilder(temp_root).build_run(result.workflow_run_id)

            relationships = {edge.relationship_type for edge in graph.edges.values()}
            self.assertIn("produces", relationships)
            self.assertIn("references", relationships)
            self.assertIn("derived_from", relationships)
            self.assertTrue(EvidenceStore(temp_root).list(result.workflow_run_id))


def _node(node_id: str, node_type: str, label: str) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        node_type=node_type,
        label=label,
        description="description",
        source_ids=[],
        evidence_ids=[],
        artifact_ids=[],
        workflow_run_ids=[],
        confidence="test",
        metadata={},
        created_at="2026-07-05T09:00:00-07:00",
        updated_at="2026-07-05T09:00:00-07:00",
    )


def _edge(edge_id: str, source: str, target: str, relationship: str) -> GraphEdge:
    return GraphEdge(
        edge_id=edge_id,
        source_node_id=source,
        target_node_id=target,
        relationship_type=relationship,
        evidence_ids=[],
        confidence="test",
        metadata={},
        created_at="2026-07-05T09:00:00-07:00",
        updated_at="2026-07-05T09:00:00-07:00",
    )


def _copy_runtime_tree(temp_root: Path) -> Path:
    for name in ["agents", "workflows", "config", "memory", "logs", "approvals", "crew", "research_inputs", "pkos_inputs"]:
        shutil.copytree(ROOT / name, temp_root / name)
    for path in (temp_root / "approvals" / "pending").glob("*.json"):
        path.unlink()
    for path in (temp_root / "approvals" / "accepted").glob("*.json"):
        path.unlink()
    for path in (temp_root / "logs" / "runs").glob("run_*"):
        shutil.rmtree(path)
    for path in (temp_root / "memory" / "runs").glob("run_*-working.json"):
        path.unlink()
    for path in (temp_root / "memory" / "evidence").glob("ev_*.json"):
        path.unlink()
    for path in [temp_root / "memory" / "evidence" / "index.json", temp_root / "memory" / "graph" / "graph.json"]:
        if path.exists():
            path.unlink()
    return temp_root


def _write_research_input(root: Path) -> Path:
    path = root / "research_inputs" / "graph-brief.md"
    path.write_text(
        "# Research Topic\n\nConcept: Evidence Engine\nTheme: Traceability\nRisk: unsupported inference\nAssumption: source lines are user supplied\nRecommendation: cite evidence IDs",
        encoding="utf-8",
    )
    return path


def _write_pkos_input(root: Path) -> Path:
    path = root / "pkos_inputs" / "graph-source.md"
    path.write_text(
        "# PKOS Topic\n\nConcept: PKOS Concept\nTheme: Traceability\nRecommendation: review before vault application",
        encoding="utf-8",
    )
    return path


def _write_provider_config(root: Path, *, invoke: bool) -> None:
    content = f"""providers:
  - id: echo
    enabled: true
    role: deterministic_stub_provider
    provider_type: echo
    model: echo-v0
    capabilities:
      - reasoning
      - structured_output
  - id: "null"
    enabled: true
    role: deterministic_noop_provider
    provider_type: "null"
    model: null-v0
    capabilities:
      - reasoning
      - structured_output

routing:
  invoke_provider_during_kernel_run: {str(invoke).lower()}
  default_provider: echo
  per_agent_provider:
    none: none
  allow_fallback: false
  fallback_provider: "null"
"""
    (root / "config" / "providers.yaml").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
