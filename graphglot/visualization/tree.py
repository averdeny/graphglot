"""AST tree visualization."""

from __future__ import annotations

import typing as t

if t.TYPE_CHECKING:
    from graphglot.ast import Expression


class ASTVisualizer:
    """Renders AST trees in various formats."""

    def __init__(self, expression: Expression):
        self.root = expression

    def to_text(self, max_depth: int | None = None) -> str:
        """Render as indented text tree with box-drawing characters.

        Args:
            max_depth: Maximum depth to render. None for unlimited.

        Returns:
            A string representation of the AST tree.
        """
        lines: list[str] = []
        self._render_node(self.root, lines, prefix="", is_last=True, depth=0, max_depth=max_depth)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, t.Any]:
        """Render as nested dict for JSON serialization.

        Returns:
            A dictionary representation of the AST tree.
        """
        return self._node_to_dict(self.root)

    def _render_node(
        self,
        node: Expression,
        lines: list[str],
        prefix: str,
        is_last: bool,
        depth: int,
        max_depth: int | None,
    ) -> None:
        """Recursively render a node and its children."""
        # Root node has no connector
        if depth == 0:
            lines.append(self._format_node(node))
        else:
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{self._format_node(node)}")

        if max_depth is not None and depth >= max_depth:
            children = list(node.children())
            if children:
                child_prefix = prefix + ("    " if is_last else "│   ")
                lines.append(f"{child_prefix}└── ... ({len(children)} children)")
            return

        children = list(node.children())
        child_prefix = prefix + ("    " if is_last or depth == 0 else "│   ")
        for i, child in enumerate(children):
            self._render_node(
                child, lines, child_prefix, i == len(children) - 1, depth + 1, max_depth
            )

    def _format_node(self, node: Expression) -> str:
        """Format a single node for display.

        Shows the node type and any scalar (non-Expression, non-list) field values.
        """
        from graphglot.ast import Expression

        type_name = node.__class__.__name__
        # Add key scalar values inline
        scalars = []
        for field in node.ast_fields:
            value = getattr(node, field, None)
            if value is not None and not isinstance(value, list | Expression):
                # Truncate long strings
                if isinstance(value, str) and len(value) > 30:
                    value = value[:27] + "..."
                scalars.append(f"{field}={value!r}")
        if scalars:
            return f"{type_name}({', '.join(scalars)})"
        return type_name

    def _node_to_dict(self, node: Expression) -> dict[str, t.Any]:
        """Convert a node to a dictionary representation."""
        from graphglot.ast import Expression

        fields: dict[str, t.Any] = {}
        for field in node.ast_fields:
            value = getattr(node, field, None)
            if value is None:
                continue
            if isinstance(value, Expression):
                # Skip - will be in children
                continue
            if isinstance(value, list):
                # Include non-Expression list items
                non_expr_items = [v for v in value if not isinstance(v, Expression)]
                if non_expr_items:
                    fields[field] = non_expr_items
            else:
                fields[field] = value

        result: dict[str, t.Any] = {
            "type": node.__class__.__name__,
        }
        if fields:
            result["fields"] = fields

        children = list(node.children())
        if children:
            result["children"] = [self._node_to_dict(c) for c in children]

        return result
