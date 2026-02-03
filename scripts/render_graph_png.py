"""Render LangGraph workflow to a Mermaid PNG."""

from pathlib import Path

from src.workflow.graph import create_newsletter_graph


def main() -> None:
    graph = create_newsletter_graph()
    compiled = graph.compile()
    png_bytes = compiled.get_graph().draw_mermaid_png()
    out_path = Path("newsletter-workflow-graph.png")
    out_path.write_bytes(png_bytes)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
