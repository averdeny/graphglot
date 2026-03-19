"""Generate API reference pages for mkdocs-gen-files."""

import mkdocs_gen_files

nav = mkdocs_gen_files.Nav()

# Public modules to document. Order determines nav order.
PUBLIC_MODULES = [
    "graphglot.dialect",
    "graphglot.parser",
    "graphglot.generator",
    "graphglot.lexer",
    "graphglot.lineage",
    "graphglot.analysis",
    "graphglot.typing",
    "graphglot.error",
    "graphglot.ast",
]

# The AST module has 500+ exports — give it special treatment.
AST_KEY_CLASSES = [
    "Expression",
    "GqlProgram",
    "MatchStatement",
    "ReturnStatement",
    "WhereClause",
    "Identifier",
]

for module_path in PUBLIC_MODULES:
    parts = module_path.split(".")
    doc_path = "/".join(parts[1:]) + ".md"  # e.g. "dialect.md"
    full_doc_path = f"reference/{doc_path}"
    nav_name = parts[-1].replace("_", " ").title()

    with mkdocs_gen_files.open(full_doc_path, "w") as fd:
        if module_path == "graphglot.ast":
            # Special handling: summary page with key classes expanded
            fd.write(f"# {nav_name}\n\n")
            fd.write(f"::: {module_path}\n")
            fd.write("    options:\n")
            fd.write("      show_root_heading: true\n")
            fd.write("      show_root_full_path: true\n")
            fd.write("      members: false\n")
            fd.write("\n")
            fd.write("## Key Classes\n\n")
            for cls_name in AST_KEY_CLASSES:
                fd.write(f"### {cls_name}\n\n")
                fd.write(f"::: graphglot.ast.{cls_name}\n")
                fd.write("    options:\n")
                fd.write("      show_root_heading: false\n")
                fd.write("      members_order: source\n")
                fd.write("\n")
        else:
            fd.write(f"# {nav_name}\n\n")
            fd.write(f"::: {module_path}\n")

    mkdocs_gen_files.set_edit_path(full_doc_path, f"../{module_path.replace('.', '/')}")
    nav[nav_name] = doc_path

# Write the nav file for literate-nav
with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
