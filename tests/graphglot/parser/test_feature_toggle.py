"""
Tests for unsupported feature validation during parsing.
"""

import pytest

from graphglot import features as F
from graphglot.dialect import Dialect
from graphglot.error import FeatureError
from graphglot.features import ALL_FEATURES, Feature

TEST_CASES = [
    pytest.param(
        F.G002,
        "MATCH DIFFERENT EDGES (n)-[e]->(m) RETURN n",
        id="G002_different_edges",
    ),
    pytest.param(
        F.G003,
        "MATCH REPEATABLE ELEMENTS (n)-[e]->(m) RETURN n",
        id="G003_repeatable_elements",
    ),
    pytest.param(
        F.G004,
        "MATCH p = (n)-[e]->(m) RETURN p",
        id="G004_path_binding",
    ),
    pytest.param(
        F.G005,
        "MATCH ALL PATHS (n)-[e]->(m) RETURN n",
        id="G005_all_paths",
    ),
    pytest.param(
        F.G006,
        "MATCH (n)-[e]->(m) KEEP WALK RETURN n",
        id="G006_keep_path_mode",
    ),
    pytest.param(
        F.G007,
        "MATCH (n)-[e]->(m) KEEP ALL PATHS RETURN n",
        id="G007_keep_path_search",
    ),
    pytest.param(
        F.G010,
        "MATCH ALL WALK PATHS (n)-[e]->(m) RETURN n",
        id="G010_explicit_walk",
    ),
    pytest.param(
        F.G011,
        "MATCH ALL TRAIL PATHS (n)-[e]->(m) RETURN n",
        id="G011_trail_mode",
    ),
    pytest.param(
        F.G012,
        "MATCH ALL SIMPLE PATHS (n)-[e]->(m) RETURN n",
        id="G012_simple_mode",
    ),
    pytest.param(
        F.G013,
        "MATCH ALL ACYCLIC PATHS (n)-[e]->(m) RETURN n",
        id="G013_acyclic_mode",
    ),
    pytest.param(
        F.G014,
        "MATCH ALL PATHS (n)-[e]->(m) RETURN n",
        id="G014_explicit_path_paths",
    ),
    pytest.param(
        F.G015,
        "MATCH ALL SIMPLE PATHS (n)-[e]->(m) RETURN n",
        id="G015_all_path_search",
    ),
    pytest.param(
        F.G016,
        "MATCH ANY (n)-[e]->(m) RETURN n",
        id="G016_any_path_search",
    ),
    pytest.param(
        F.G017,
        "MATCH ALL SHORTEST (n)-[e]->(m) RETURN n",
        id="G017_all_shortest_path_search",
    ),
    pytest.param(
        F.G018,
        "MATCH ANY SHORTEST (n)-[e]->(m) RETURN n",
        id="G018_any_shortest_path_search",
    ),
    pytest.param(
        F.G019,
        "MATCH SHORTEST 5 (n)-[e]->(m) RETURN n",
        id="G019_counted_shortest_path_search",
    ),
    pytest.param(
        F.G020,
        "MATCH SHORTEST 3 GROUP (n)-[e]->(m) RETURN n",
        id="G020_counted_shortest_group_search",
    ),
    pytest.param(
        F.G030,
        "MATCH (a)-[e1]->(b) |+| (c)-[e2]->(d) RETURN a",
        id="G030_path_multiset_alternation",
    ),
    pytest.param(
        F.G031,
        "MATCH (a)-[e1]->(b)* |+| (c)-[e2]->(d) RETURN a",
        id="G031_path_multiset_alternation_variable_length",
    ),
    pytest.param(
        F.G032,
        "MATCH (a)-[e1]->(b) | (c)-[e2]->(d) RETURN a",
        id="G032_path_pattern_union",
    ),
    pytest.param(
        F.G033,
        "MATCH (a)-[e1]->(b)* | (c)-[e2]->(d) RETURN a",
        id="G033_path_pattern_union_variable_length",
    ),
    pytest.param(
        F.G035,
        "MATCH ((a)-[e]->(b))* RETURN a",
        id="G035_quantified_paths",
    ),
    pytest.param(
        F.G036,
        "MATCH (a)-[e]->{1,5}(b) RETURN a",
        id="G036_quantified_edges",
    ),
    pytest.param(
        F.G037,
        "MATCH (a)-[e]->(b)? RETURN a",
        id="G037_questioned_paths",
    ),
    pytest.param(
        F.G038,
        "MATCH ((a)-[e]->(b)) RETURN a",
        id="G038_parenthesized_path_pattern",
    ),
    pytest.param(
        F.G039,
        "MATCH ~/ Person /~ RETURN 1",
        id="G039_simplified_defaulting_undirected",
    ),
    pytest.param(
        F.G039,
        "MATCH <~/ Person /~ RETURN 1",
        id="G039_simplified_defaulting_left_or_undirected",
    ),
    pytest.param(
        F.G039,
        "MATCH ~/ Person /~> RETURN 1",
        id="G039_simplified_defaulting_undirected_or_right",
    ),
    pytest.param(
        F.G041,
        "MATCH (a)-[e WHERE a.age > 5]->(b) RETURN a",
        id="G041_non_local_element_pattern_predicate",
    ),
    pytest.param(
        F.G043,
        "MATCH (a)~[r]~(b) RETURN a",
        id="G043_full_edge_undirected",
    ),
    pytest.param(
        F.G043,
        "MATCH (a)<~[r]~(b) RETURN a",
        id="G043_full_edge_left_or_undirected",
    ),
    pytest.param(
        F.G043,
        "MATCH (a)~[r]~>(b) RETURN a",
        id="G043_full_edge_undirected_or_right",
    ),
    pytest.param(
        F.G043,
        "MATCH (a)<-[r]->(b) RETURN a",
        id="G043_full_edge_left_or_right",
    ),
    pytest.param(
        F.G044,
        "MATCH (a)<-(b) RETURN a",
        id="G044_abbreviated_left_arrow",
    ),
    pytest.param(
        F.G044,
        "MATCH (a)->(b) RETURN a",
        id="G044_abbreviated_right_arrow",
    ),
    pytest.param(
        F.G044,
        "MATCH (a)-(b) RETURN a",
        id="G044_abbreviated_minus_sign",
    ),
    pytest.param(
        F.G045,
        "MATCH (a)~(b) RETURN a",
        id="G045_abbreviated_tilde",
    ),
    pytest.param(
        F.G045,
        "MATCH (a)<~(b) RETURN a",
        id="G045_abbreviated_left_arrow_tilde",
    ),
    pytest.param(
        F.G045,
        "MATCH (a)~>(b) RETURN a",
        id="G045_abbreviated_tilde_right_arrow",
    ),
    pytest.param(
        F.G045,
        "MATCH (a)<->(b) RETURN a",
        id="G045_abbreviated_left_minus_right",
    ),
    pytest.param(
        F.G046,
        "MATCH (a)(b) RETURN a",
        id="G046_adjacent_vertex_patterns",
    ),
    pytest.param(
        F.G047,
        "MATCH -[r]-> RETURN a",
        id="G047_relaxed_topological_consistency_concise_edge",
    ),
    pytest.param(
        F.G048,
        "MATCH (p = (a)-[e]->(b)) RETURN a",
        id="G048_parenthesized_path_pattern_subpath_variable",
    ),
    pytest.param(
        F.G049,
        "MATCH (WALK (a)-[e]->(b)) RETURN a",
        id="G049_parenthesized_path_pattern_path_mode_prefix",
    ),
    pytest.param(
        F.G050,
        "MATCH ((a)-[e]->(b) WHERE e.weight > 5) RETURN a",
        id="G050_parenthesized_path_pattern_where_clause",
    ),
    pytest.param(
        F.G051,
        "MATCH (a)-[e]->((b)-[f]->(c) WHERE a.age > 5) RETURN a",
        id="G051_parenthesized_path_pattern_non_local_predicate",
    ),
    pytest.param(
        F.G060,
        "MATCH (n:Person){3} RETURN n",
        id="G060_bounded_graph_pattern_quantifier_fixed",
    ),
    pytest.param(
        F.G060,
        "MATCH (n:Person){1,5} RETURN n",
        id="G060_bounded_graph_pattern_quantifier_general",
    ),
    pytest.param(
        F.G061,
        "MATCH (n:Person){3,} RETURN n",
        id="G061_unbounded_graph_pattern_quantifiers_asterisk",
    ),
    pytest.param(
        F.G061,
        "MATCH (n:Person){1,} RETURN n",
        id="G061_unbounded_graph_pattern_quantifiers_general",
    ),
    pytest.param(
        F.G074,
        "MATCH (n:%) RETURN n",
        id="G074_wildcard_label",
    ),
    pytest.param(
        F.G080,
        "MATCH <-/ Person /- RETURN 1",
        id="G080_simplified_defaulting_left",
    ),
    pytest.param(
        F.G080,
        "MATCH -/ Person /-> RETURN 1",
        id="G080_simplified_defaulting_right",
    ),
    pytest.param(
        F.G080,
        "MATCH -/ Person /- RETURN 1",
        id="G080_simplified_defaulting_any_direction",
    ),
    pytest.param(
        F.G081,
        "MATCH -/ <~ Person /- RETURN 1",
        id="G081_simplified_direction_override_left_or_undirected",
    ),
    pytest.param(
        F.G081,
        "MATCH -/ ~ Person > /- RETURN 1",
        id="G081_simplified_direction_override_undirected_or_right",
    ),
    pytest.param(
        F.G081,
        "MATCH -/ <~ !Person /- RETURN 1",
        id="G081_simplified_direction_override_left_or_undirected_negated",
    ),
    pytest.param(
        F.G082,
        "MATCH -/ < Person /- RETURN 1",
        id="G082_simplified_direction_override_left",
    ),
    pytest.param(
        F.G082,
        "MATCH -/ - Person /- RETURN 1",
        id="G082_simplified_direction_override_any_direction",
    ),
    pytest.param(
        F.G082,
        "MATCH -/ < !Person /- RETURN 1",
        id="G082_simplified_direction_override_left_negated",
    ),
    pytest.param(
        F.G100,
        "MATCH (n) RETURN ELEMENT_ID(n)",
        id="G100_element_id_function",
    ),
    pytest.param(
        F.G110,
        "MATCH (n)-[e]->(m) WHERE e IS DIRECTED RETURN e",
        id="G110_is_directed_predicate",
    ),
    pytest.param(
        F.G111,
        "MATCH (n:Person) WHERE n:Person RETURN n",
        id="G111_is_labeled_predicate",
    ),
    pytest.param(
        F.G112,
        "MATCH (n)-[e]->(m) WHERE n IS SOURCE OF e RETURN n",
        id="G112_is_source_of_predicate",
    ),
    pytest.param(
        F.G112,
        "MATCH (n)-[e]->(m) WHERE m IS DESTINATION OF e RETURN m",
        id="G112_is_destination_of_predicate",
    ),
    pytest.param(
        F.G112,
        "MATCH (n)-[e]->(m) WHERE n IS NOT SOURCE OF e RETURN n",
        id="G112_is_not_source_of_predicate",
    ),
    pytest.param(
        F.G113,
        "MATCH (a)-[e1]->(b), (c)-[e2]->(d) WHERE ALL_DIFFERENT(a,c) RETURN a",
        id="G113_all_different_predicate",
    ),
    pytest.param(
        F.G114,
        "MATCH (a)-[e1]->(b), (c)-[e2]->(d) WHERE SAME(a,c) RETURN a",
        id="G114_same_predicate",
    ),
    pytest.param(
        F.G115,
        "MATCH (n:Person) WHERE PROPERTY_EXISTS(n, name) RETURN n",
        id="G115_property_exists_predicate",
    ),
    pytest.param(
        F.GA03,
        "MATCH (n) RETURN n ORDER BY n.name NULLS FIRST",
        id="GA03_explicit_null_ordering",
    ),
    pytest.param(
        F.GA05,
        "MATCH (n) RETURN CAST(n.prop AS STRING)",
        id="GA05_cast_specification",
    ),
    pytest.param(
        F.GA06,
        "MATCH (n) WHERE n.age IS TYPED INT32 RETURN n",
        id="GA06_value_type_predicate_typed",
    ),
    pytest.param(
        F.GA06,
        "MATCH (n) WHERE n.age IS NOT TYPED INT32 RETURN n",
        id="GA06_value_type_predicate_not_typed",
    ),
    # GB01: Long identifiers
    pytest.param(
        F.GB01,
        f"MATCH (n) RETURN n.{'a' * 128}",
        id="GB01_long_identifier",
    ),
    # GB02: Double minus sign comments
    pytest.param(
        F.GB02,
        "-- comment\nMATCH (n) RETURN n",
        id="GB02_double_minus_sign_comment",
    ),
    # GB03: Double solidus comments
    pytest.param(
        F.GB03,
        "// comment\nMATCH (n) RETURN n",
        id="GB03_double_solidus_comment",
    ),
    pytest.param(
        F.GC01,
        "CREATE SCHEMA /myschemas/foo",
        id="GC01_create_schema_statement",
    ),
    pytest.param(
        F.GC01,
        "DROP SCHEMA /myschemas/foo",
        id="GC01_drop_schema_statement",
    ),
    pytest.param(
        F.GC02,
        "CREATE SCHEMA IF NOT EXISTS /myschemas/bar",
        id="GC02_create_schema_if_not_exists",
    ),
    pytest.param(
        F.GC02,
        "DROP SCHEMA IF EXISTS /myschemas/bar",
        id="GC02_drop_schema_if_exists",
    ),
    pytest.param(
        F.GC03,
        "CREATE PROPERTY GRAPH TYPE IF NOT EXISTS my_type LIKE CURRENT_GRAPH",
        id="GC03_create_graph_type_if_not_exists_property",
    ),
    pytest.param(
        F.GC03,
        "DROP GRAPH TYPE IF EXISTS my_type",
        id="GC03_drop_graph_type_if_exists",
    ),
    pytest.param(
        F.GC04,
        "CREATE PROPERTY GRAPH my_graph_of_type LIKE CURRENT_GRAPH",
        id="GC04_create_graph_statement",
    ),
    pytest.param(
        F.GC04,
        "DROP GRAPH my_graph",
        id="GC04_drop_graph_statement",
    ),
    pytest.param(
        F.GC05,
        "CREATE PROPERTY GRAPH IF NOT EXISTS my_graph LIKE CURRENT_GRAPH AS COPY OF CURRENT_GRAPH",
        id="GC05_create_graph_if_not_exists_with_source",
    ),
    pytest.param(
        F.GC05,
        "DROP PROPERTY GRAPH IF EXISTS my_graph",
        id="GC05_drop_graph_if_exists_property",
    ),
    pytest.param(
        F.GD01,
        "SET n.prop = 1",
        id="GD01_set_property_primitive_data_modifying",
    ),
    pytest.param(
        F.GD01,
        "CALL my_proc() RETURN 1",
        id="GD01_call_data_modifying_procedure_statement",
    ),
    pytest.param(
        F.GD02,
        "MATCH (n:Person) SET n:Employee",
        id="GD02_set_label_item",
    ),
    pytest.param(
        F.GD02,
        "MATCH (n:Person) REMOVE n:Person RETURN n",
        id="GD02_remove_label_item",
    ),
    pytest.param(
        F.GD03,
        "DELETE TABLE { MATCH (n) RETURN n }",
        id="GD03_delete_subquery",
    ),
    pytest.param(
        F.GD04,
        "DELETE n.prop",
        id="GD04_delete_property_reference",
    ),
    pytest.param(
        F.GE01,
        "RETURN GRAPH my_graph",
        id="GE01_graph_reference_value_expression",
    ),
    pytest.param(
        F.GE02,
        "RETURN TABLE { MATCH (n) RETURN n }",
        id="GE02_binding_table_reference_value_expression",
    ),
    pytest.param(
        F.GE03,
        "RETURN LET x = 1 IN x + 1 END",
        id="GE03_let_value_expression",
    ),
    pytest.param(
        F.GE06,
        "RETURN PATH [a] || PATH [b]",
        id="GE06_path_value_concatenation",
    ),
    pytest.param(
        F.GE06,
        "RETURN PATH [n]",
        id="GE06_path_value_constructor",
    ),
    pytest.param(
        F.GE07,
        "MATCH (n) WHERE TRUE XOR FALSE RETURN n",
        id="GE07_boolean_xor",
    ),
    pytest.param(
        F.GE08,
        "RETURN GRAPH $$my_graph",
        id="GE08_reference_parameter_specification",
    ),
    # GF01: Enhanced numeric functions
    pytest.param(
        F.GF01,
        "RETURN ABS(-5)",
        id="GF01_absolute_value_expression",
    ),
    pytest.param(
        F.GF01,
        "RETURN MOD(10, 3)",
        id="GF01_modulus_expression",
    ),
    pytest.param(
        F.GF01,
        "RETURN FLOOR(3.7)",
        id="GF01_floor_function",
    ),
    pytest.param(
        F.GF01,
        "RETURN CEILING(3.2)",
        id="GF01_ceiling_function",
    ),
    pytest.param(
        F.GF01,
        "RETURN SQRT(16)",
        id="GF01_square_root",
    ),
    # GF02: Trigonometric functions
    pytest.param(
        F.GF02,
        "RETURN SIN(1)",
        id="GF02_trigonometric_sin",
    ),
    pytest.param(
        F.GF02,
        "RETURN COS(1)",
        id="GF02_trigonometric_cos",
    ),
    # GF03: Logarithmic functions
    pytest.param(
        F.GF03,
        "RETURN LOG(2, 8)",
        id="GF03_general_logarithm",
    ),
    pytest.param(
        F.GF03,
        "RETURN LOG10(100)",
        id="GF03_common_logarithm",
    ),
    pytest.param(
        F.GF03,
        "RETURN LN(2.718)",
        id="GF03_natural_logarithm",
    ),
    pytest.param(
        F.GF03,
        "RETURN EXP(1)",
        id="GF03_exponential_function",
    ),
    pytest.param(
        F.GF03,
        "RETURN POWER(2, 3)",
        id="GF03_power_function",
    ),
    # GF04: Enhanced path functions
    pytest.param(
        F.GF04,
        "MATCH p = (a)-[]->(b) RETURN ELEMENTS(p)",
        id="GF04_elements_function",
    ),
    pytest.param(
        F.GF04,
        "MATCH p = (a)-[]->(b) RETURN PATH_LENGTH(p)",
        id="GF04_path_length_expression",
    ),
    # GF05: Multi-character TRIM function
    pytest.param(
        F.GF05,
        'RETURN LTRIM("hello")',
        id="GF05_ltrim",
    ),
    pytest.param(
        F.GF05,
        'RETURN RTRIM("hello")',
        id="GF05_rtrim",
    ),
    # GF06: Explicit TRIM function (with FROM)
    pytest.param(
        F.GF06,
        'RETURN TRIM(LEADING FROM "hello")',
        id="GF06_trim_leading_from",
    ),
    pytest.param(
        F.GF06,
        'RETURN TRIM(TRAILING FROM "hello")',
        id="GF06_trim_trailing_from",
    ),
    # GF07: Byte string TRIM function - requires byte string context
    pytest.param(
        F.GF07,
        "RETURN TRIM(X'00' FROM X'001122')",
        id="GF07_byte_string_trim",
    ),
    # GF10: Advanced aggregate functions
    pytest.param(
        F.GF10,
        "MATCH (n) RETURN COLLECT_LIST(n.name)",
        id="GF10_collect_list",
    ),
    pytest.param(
        F.GF10,
        "MATCH (n) RETURN STDDEV_SAMP(n.age)",
        id="GF10_stddev_samp",
    ),
    pytest.param(
        F.GF10,
        "MATCH (n) RETURN STDDEV_POP(n.age)",
        id="GF10_stddev_pop",
    ),
    # GF11: Advanced aggregate functions: binary set functions
    pytest.param(
        F.GF11,
        "MATCH (n) RETURN PERCENTILE_CONT(n.score, 0.5)",
        id="GF11_percentile_cont",
    ),
    pytest.param(
        F.GF11,
        "MATCH (n) RETURN PERCENTILE_DISC(n.score, 0.5)",
        id="GF11_percentile_disc",
    ),
    # GF12: CARDINALITY function
    pytest.param(
        F.GF12,
        "RETURN CARDINALITY([1, 2, 3])",
        id="GF12_cardinality",
    ),
    # GF13: SIZE function
    pytest.param(
        F.GF13,
        "RETURN SIZE([1, 2, 3])",
        id="GF13_size",
    ),
    # GF20: Aggregate functions in sort keys
    pytest.param(
        F.GF20,
        "MATCH (n) RETURN n.name AS name ORDER BY COUNT(*)",
        id="GF20_aggregate_in_sort_key",
    ),
    # GG01: Graph with an open graph type
    pytest.param(
        F.GG01,
        "CREATE PROPERTY GRAPH my_graph ANY PROPERTY GRAPH",
        id="GG01_open_graph_type",
    ),
    # GG02: Graph with a closed graph type
    pytest.param(
        F.GG02,
        "CREATE PROPERTY GRAPH my_graph LIKE CURRENT_GRAPH",
        id="GG02_of_graph_type",
    ),
    pytest.param(
        F.GG02,
        "CREATE PROPERTY GRAPH TYPE my_type LIKE CURRENT_GRAPH",
        id="GG02_create_graph_type_statement",
    ),
    pytest.param(
        F.GG02,
        "DROP GRAPH TYPE my_type",
        id="GG02_drop_graph_type_statement",
    ),
    # GG03: Graph type inline specification
    pytest.param(
        F.GG03,
        "CREATE PROPERTY GRAPH my_graph { (n) }",
        id="GG03_nested_graph_type_specification",
    ),
    # GG04: Graph type like a graph
    pytest.param(
        F.GG04,
        "CREATE PROPERTY GRAPH my_graph LIKE CURRENT_GRAPH",
        id="GG04_graph_type_like_graph",
    ),
    # GG05: Graph from a graph source
    pytest.param(
        F.GG05,
        "CREATE PROPERTY GRAPH my_graph LIKE CURRENT_GRAPH AS COPY OF CURRENT_GRAPH",
        id="GG05_graph_source",
    ),
    # GG20: Explicit element type names
    pytest.param(
        F.GG20,
        "CREATE GRAPH TYPE my_type { NODE TYPE Person }",
        id="GG20_node_type_name",
    ),
    pytest.param(
        F.GG20,
        "CREATE GRAPH TYPE my_type { DIRECTED EDGE TYPE Knows CONNECTING (a -> b) }",
        id="GG20_edge_type_name",
    ),
    # GG21: Explicit element type key label sets
    pytest.param(
        F.GG21,
        "CREATE GRAPH TYPE my_type { NODE TYPE :Person => }",
        id="GG21_node_type_key_label_set",
    ),
    pytest.param(
        F.GG21,
        "CREATE GRAPH TYPE my_type { DIRECTED EDGE TYPE :Knows => CONNECTING (a -> b) }",
        id="GG21_edge_type_key_label_set",
    ),
    # GH02: Undirected edge patterns
    pytest.param(
        F.GH02,
        "INSERT ()~[e]~()",
        id="GH02_insert_edge_undirected",
    ),
    pytest.param(
        F.GH02,
        "CREATE GRAPH TYPE my_type { (a)~[:Knows]~(b) }",
        id="GH02_edge_type_pattern_undirected",
    ),
    pytest.param(
        F.GH02,
        "CREATE GRAPH TYPE my_type { UNDIRECTED EDGE TYPE Knows CONNECTING (a ~ b) }",
        id="GH02_edge_type_phrase_undirected",
    ),
    # GP01: Inline procedure
    pytest.param(
        F.GP01,
        "MATCH (n) CALL { MATCH (m) RETURN m } RETURN n",
        id="GP01_inline_procedure_call",
    ),
    # GP02: Inline procedure with implicit nested variable scope
    pytest.param(
        F.GP02,
        "MATCH (n) CALL { MATCH (m) RETURN m } RETURN n",
        id="GP02_inline_procedure_implicit_scope",
    ),
    # GP03: Inline procedure with explicit nested variable scope
    pytest.param(
        F.GP03,
        "MATCH (n) CALL (n) { MATCH (n)-[]->(m) RETURN m } RETURN n",
        id="GP03_inline_procedure_explicit_scope",
    ),
    # GP04: Named procedure calls
    pytest.param(
        F.GP04,
        "CALL my_proc() YIELD result RETURN result",
        id="GP04_named_procedure_call",
    ),
    pytest.param(
        F.GP04,
        "CALL my.namespace.proc(a, b) YIELD x RETURN x",
        id="GP04_named_procedure_call_with_namespace",
    ),
    # GP05: Procedure-local value variable definitions
    pytest.param(
        F.GP05,
        "VALUE x = 1 MATCH (n) RETURN n",
        id="GP05_value_variable_definition",
    ),
    # GP06: Value variables based on simple expressions
    pytest.param(
        F.GP06,
        "VALUE x = 1 MATCH (n) RETURN n",
        id="GP06_value_variable_simple_expression",
    ),
    # GP07: Value variables based on subqueries
    pytest.param(
        F.GP07,
        "VALUE x = VALUE { MATCH (n) RETURN n.prop } MATCH (m) RETURN m",
        id="GP07_value_variable_subquery",
    ),
    # GP08: Procedure-local binding table variable definitions
    pytest.param(
        F.GP08,
        "TABLE t = { MATCH (n) RETURN n } MATCH (m) RETURN m",
        id="GP08_binding_table_variable_definition",
    ),
    # GP09: Binding table variables based on simple expressions or references
    pytest.param(
        F.GP09,
        "TABLE t = my_table MATCH (n) RETURN n",
        id="GP09_binding_table_variable_reference",
    ),
    # GP10: Binding table variables based on subqueries
    pytest.param(
        F.GP10,
        "TABLE t = { MATCH (n) RETURN n } MATCH (m) RETURN m",
        id="GP10_binding_table_variable_subquery",
    ),
    # GP11: Procedure-local graph variable definitions
    pytest.param(
        F.GP11,
        "GRAPH g = my_graph MATCH (n) RETURN n",
        id="GP11_graph_variable_definition",
    ),
    # GP12: Graph variables based on simple expressions or references
    pytest.param(
        F.GP12,
        "GRAPH g = my_graph MATCH (n) RETURN n",
        id="GP12_graph_variable_simple_expression",
    ),
    # GP13: Graph variables based on subqueries
    pytest.param(
        F.GP13,
        "GRAPH g = VALUE { MATCH (n) RETURN n } MATCH (m) RETURN m",
        id="GP13_graph_variable_subquery",
    ),
    # GP16: AT schema clause in procedure body
    pytest.param(
        F.GP16,
        "CALL { AT /myschemas/foo MATCH (n) RETURN n } RETURN 1",
        id="GP16_at_schema_clause_in_procedure",
    ),
    # GP17: Binding variable definition block in procedure body
    pytest.param(
        F.GP17,
        "CALL { VALUE x = 1 MATCH (n) RETURN n } RETURN 1",
        id="GP17_binding_variable_definition_block",
    ),
    # GQ01: USE graph clause
    pytest.param(
        F.GQ01,
        "USE my_graph MATCH (n) RETURN n",
        id="GQ01_use_graph_clause",
    ),
    # GQ02: Composite query: OTHERWISE
    pytest.param(
        F.GQ02,
        "MATCH (n:Cat) RETURN n OTHERWISE MATCH (m:Dog) RETURN m",
        id="GQ02_composite_query_otherwise",
    ),
    # GQ03: Composite query: UNION
    pytest.param(
        F.GQ03,
        "MATCH (n) RETURN n UNION MATCH (m) RETURN m",
        id="GQ03_composite_query_union",
    ),
    # GQ04: Composite query: EXCEPT DISTINCT
    pytest.param(
        F.GQ04,
        "MATCH (n) RETURN n EXCEPT MATCH (m) RETURN m",
        id="GQ04_composite_query_except",
    ),
    pytest.param(
        F.GQ04,
        "MATCH (n) RETURN n EXCEPT DISTINCT MATCH (m) RETURN m",
        id="GQ04_composite_query_except_distinct",
    ),
    # GQ05: Composite query: EXCEPT ALL
    pytest.param(
        F.GQ05,
        "MATCH (n) RETURN n EXCEPT ALL MATCH (m) RETURN m",
        id="GQ05_composite_query_except_all",
    ),
    # GQ06: Composite query: INTERSECT DISTINCT
    pytest.param(
        F.GQ06,
        "MATCH (n) RETURN n INTERSECT MATCH (m) RETURN m",
        id="GQ06_composite_query_intersect",
    ),
    pytest.param(
        F.GQ06,
        "MATCH (n) RETURN n INTERSECT DISTINCT MATCH (m) RETURN m",
        id="GQ06_composite_query_intersect_distinct",
    ),
    # GQ07: Composite query: INTERSECT ALL
    pytest.param(
        F.GQ07,
        "MATCH (n) RETURN n INTERSECT ALL MATCH (m) RETURN m",
        id="GQ07_composite_query_intersect_all",
    ),
    # GQ08: FILTER statement
    pytest.param(
        F.GQ08,
        "MATCH (n) FILTER WHERE n.age > 21 RETURN n",
        id="GQ08_filter_statement",
    ),
    # GQ09: LET statement
    pytest.param(
        F.GQ09,
        "MATCH (n) LET x = n.age RETURN x",
        id="GQ09_let_statement",
    ),
    # GQ10: FOR statement with list value expression
    pytest.param(
        F.GQ10,
        "FOR x IN [1, 2, 3] RETURN x",
        id="GQ10_for_statement_list_value",
    ),
    # GQ11: FOR statement with WITH ORDINALITY
    pytest.param(
        F.GQ11,
        "FOR x IN [1, 2, 3] WITH ORDINALITY i RETURN x, i",
        id="GQ11_for_statement_with_ordinality",
    ),
    # GQ12: ORDER BY and page statement: OFFSET clause
    pytest.param(
        F.GQ12,
        "MATCH (n) RETURN n ORDER BY n.name OFFSET 10",
        id="GQ12_offset_clause",
    ),
    # GQ13: ORDER BY and page statement: LIMIT clause
    pytest.param(
        F.GQ13,
        "MATCH (n) RETURN n ORDER BY n.name LIMIT 10",
        id="GQ13_limit_clause",
    ),
    # GQ14: Complex expressions in sort keys
    pytest.param(
        F.GQ14,
        "MATCH (n) RETURN n.name AS name ORDER BY n.name || n.surname",
        id="GQ14_complex_sort_key_expression",
    ),
    # GQ15: GROUP BY clause
    pytest.param(
        F.GQ15,
        "MATCH (n) RETURN n GROUP BY n",
        id="GQ15_group_by_clause",
    ),
    # GQ16: Pre-projection aliases in sort keys
    pytest.param(
        F.GQ16,
        "MATCH (n) RETURN n.name AS alias ORDER BY alias",
        id="GQ16_pre_projection_alias_in_sort_key",
    ),
    # GQ18: Scalar subqueries
    pytest.param(
        F.GQ18,
        "MATCH (n) RETURN VALUE { MATCH (m) RETURN m.x }",
        id="GQ18_scalar_subquery",
    ),
    # GQ19: Graph pattern YIELD clause
    pytest.param(
        F.GQ19,
        "MATCH (n)-[e]->(m) YIELD n, m RETURN n",
        id="GQ19_graph_pattern_yield_clause",
    ),
    # GQ20: Advanced linear composition with NEXT
    pytest.param(
        F.GQ20,
        "MATCH (n) NEXT RETURN n",
        id="GQ20_next_statement",
    ),
    # GQ21: OPTIONAL: Multiple MATCH statements
    pytest.param(
        F.GQ21,
        "OPTIONAL { MATCH (n) MATCH (m) } RETURN n, m",
        id="GQ21_optional_multiple_match",
    ),
    # GQ22: EXISTS predicate: multiple MATCH statements
    pytest.param(
        F.GQ22,
        "MATCH (n) WHERE EXISTS { MATCH (n) MATCH (m) } RETURN n",
        id="GQ22_exists_multiple_match",
    ),
    # GQ23: FOR statement: binding table support
    pytest.param(
        F.GQ23,
        "FOR x IN TABLE t RETURN x",
        id="GQ23_for_binding_table",
    ),
    # GQ24: FOR statement: WITH OFFSET
    pytest.param(
        F.GQ24,
        "FOR x IN [1, 2, 3] WITH OFFSET i RETURN x, i",
        id="GQ24_for_statement_with_offset",
    ),
    # GS01: SESSION SET command: session-local graph parameters
    # Parser ambiguity: SESSION SET GRAPH matches SessionSetGraphClause before
    # SessionSetGraphParameterClause gets tried. Feature check is on the AST class.
    pytest.param(
        F.GS01,
        "SESSION SET GRAPH $g = my_graph",
        id="GS01_session_set_graph_parameter",
    ),
    # GS02: SESSION SET command: session-local binding table parameters
    pytest.param(
        F.GS02,
        "SESSION SET TABLE $t = my_table",
        id="GS02_session_set_binding_table_parameter",
    ),
    # GS03: SESSION SET command: session-local value parameters
    pytest.param(
        F.GS03,
        "SESSION SET VALUE $v = 42",
        id="GS03_session_set_value_parameter",
    ),
    # GS04: SESSION RESET command: reset all characteristics
    pytest.param(
        F.GS04,
        "SESSION RESET CHARACTERISTICS",
        id="GS04_session_reset_characteristics",
    ),
    # GS05: SESSION RESET command: reset session schema
    pytest.param(
        F.GS05,
        "SESSION RESET SCHEMA",
        id="GS05_session_reset_schema",
    ),
    # GS06: SESSION RESET command: reset session graph
    pytest.param(
        F.GS06,
        "SESSION RESET GRAPH",
        id="GS06_session_reset_graph",
    ),
    # GS07: SESSION RESET command: reset time zone displacement
    pytest.param(
        F.GS07,
        "SESSION RESET TIME ZONE",
        id="GS07_session_reset_time_zone",
    ),
    # GS08: SESSION RESET command: reset all session parameters
    pytest.param(
        F.GS08,
        "SESSION RESET ALL PARAMETERS",
        id="GS08_session_reset_all_parameters",
    ),
    # GS15: SESSION SET command: set time zone displacement
    pytest.param(
        F.GS15,
        "SESSION SET TIME ZONE 'UTC'",
        id="GS15_session_set_time_zone",
    ),
    # GS16: SESSION RESET command: reset individual session parameters
    pytest.param(
        F.GS16,
        "SESSION RESET PARAMETER $my_param",
        id="GS16_session_reset_individual_parameter",
    ),
    # GT01: Explicit transaction commands
    pytest.param(
        F.GT01,
        "START TRANSACTION",
        id="GT01_start_transaction",
    ),
    # GT02: Specified transaction characteristics
    pytest.param(
        F.GT02,
        "START TRANSACTION READ ONLY",
        id="GT02_specified_transaction_characteristics",
    ),
    # GV01: 8 bit unsigned integer numbers
    pytest.param(
        F.GV01,
        "MATCH (n) WHERE n.age IS TYPED UINT8 RETURN n",
        id="GV01_uint8",
    ),
    pytest.param(
        F.GV01,
        "MATCH (n) WHERE n.age IS TYPED UNSIGNED INTEGER8 RETURN n",
        id="GV01_unsigned_integer8",
    ),
    # GV02: 8 bit signed integer numbers
    pytest.param(
        F.GV02,
        "MATCH (n) WHERE n.age IS TYPED INT8 RETURN n",
        id="GV02_int8",
    ),
    pytest.param(
        F.GV02,
        "MATCH (n) WHERE n.age IS TYPED SIGNED INTEGER8 RETURN n",
        id="GV02_signed_integer8",
    ),
    pytest.param(
        F.GV02,
        "MATCH (n) WHERE n.age IS TYPED INTEGER8 RETURN n",
        id="GV02_integer8",
    ),
    # GV03: 16 bit unsigned integer numbers
    pytest.param(
        F.GV03,
        "MATCH (n) WHERE n.age IS TYPED UINT16 RETURN n",
        id="GV03_uint16",
    ),
    pytest.param(
        F.GV03,
        "MATCH (n) WHERE n.age IS TYPED UNSIGNED INTEGER16 RETURN n",
        id="GV03_unsigned_integer16",
    ),
    # GV04: 16 bit signed integer numbers
    pytest.param(
        F.GV04,
        "MATCH (n) WHERE n.age IS TYPED INT16 RETURN n",
        id="GV04_int16",
    ),
    pytest.param(
        F.GV04,
        "MATCH (n) WHERE n.age IS TYPED SIGNED INTEGER16 RETURN n",
        id="GV04_signed_integer16",
    ),
    pytest.param(
        F.GV04,
        "MATCH (n) WHERE n.age IS TYPED INTEGER16 RETURN n",
        id="GV04_integer16",
    ),
    # GV05: Small unsigned integer numbers
    pytest.param(
        F.GV05,
        "MATCH (n) WHERE n.age IS TYPED USMALLINT RETURN n",
        id="GV05_usmallint",
    ),
    pytest.param(
        F.GV05,
        "MATCH (n) WHERE n.age IS TYPED UNSIGNED SMALL INTEGER RETURN n",
        id="GV05_unsigned_small_integer",
    ),
    # GV06: 32 bit unsigned integer numbers
    pytest.param(
        F.GV06,
        "MATCH (n) WHERE n.age IS TYPED UINT32 RETURN n",
        id="GV06_uint32",
    ),
    pytest.param(
        F.GV06,
        "MATCH (n) WHERE n.age IS TYPED UNSIGNED INTEGER32 RETURN n",
        id="GV06_unsigned_integer32",
    ),
    # GV07: 32 bit signed integer numbers
    pytest.param(
        F.GV07,
        "MATCH (n) WHERE n.age IS TYPED INT32 RETURN n",
        id="GV07_int32",
    ),
    pytest.param(
        F.GV07,
        "MATCH (n) WHERE n.age IS TYPED SIGNED INTEGER32 RETURN n",
        id="GV07_signed_integer32",
    ),
    pytest.param(
        F.GV07,
        "MATCH (n) WHERE n.age IS TYPED INTEGER32 RETURN n",
        id="GV07_integer32",
    ),
    # GV08: Regular unsigned integer numbers
    pytest.param(
        F.GV08,
        "MATCH (n) WHERE n.age IS TYPED UINT RETURN n",
        id="GV08_uint",
    ),
    pytest.param(
        F.GV08,
        "MATCH (n) WHERE n.age IS TYPED UNSIGNED INTEGER RETURN n",
        id="GV08_unsigned_integer",
    ),
    # GV09: Specified integer number precision
    pytest.param(
        F.GV09,
        "MATCH (n) WHERE n.age IS TYPED INT(10) RETURN n",
        id="GV09_int_with_precision",
    ),
    pytest.param(
        F.GV09,
        "MATCH (n) WHERE n.age IS TYPED INTEGER(10) RETURN n",
        id="GV09_integer_with_precision",
    ),
    # GV10: Big unsigned integer numbers
    pytest.param(
        F.GV10,
        "MATCH (n) WHERE n.age IS TYPED UBIGINT RETURN n",
        id="GV10_ubigint",
    ),
    pytest.param(
        F.GV10,
        "MATCH (n) WHERE n.age IS TYPED UNSIGNED BIG INTEGER RETURN n",
        id="GV10_unsigned_big_integer",
    ),
    # GV11: 64 bit unsigned integer numbers
    pytest.param(
        F.GV11,
        "MATCH (n) WHERE n.age IS TYPED UINT64 RETURN n",
        id="GV11_uint64",
    ),
    pytest.param(
        F.GV11,
        "MATCH (n) WHERE n.age IS TYPED UNSIGNED INTEGER64 RETURN n",
        id="GV11_unsigned_integer64",
    ),
    # GV12: 64 bit signed integer numbers
    pytest.param(
        F.GV12,
        "MATCH (n) WHERE n.age IS TYPED INT64 RETURN n",
        id="GV12_int64",
    ),
    pytest.param(
        F.GV12,
        "MATCH (n) WHERE n.age IS TYPED SIGNED INTEGER64 RETURN n",
        id="GV12_signed_integer64",
    ),
    pytest.param(
        F.GV12,
        "MATCH (n) WHERE n.age IS TYPED INTEGER64 RETURN n",
        id="GV12_integer64",
    ),
    # GV13: 128 bit unsigned integer numbers
    pytest.param(
        F.GV13,
        "MATCH (n) WHERE n.age IS TYPED UINT128 RETURN n",
        id="GV13_uint128",
    ),
    pytest.param(
        F.GV13,
        "MATCH (n) WHERE n.age IS TYPED UNSIGNED INTEGER128 RETURN n",
        id="GV13_unsigned_integer128",
    ),
    # GV14: 128 bit signed integer numbers
    pytest.param(
        F.GV14,
        "MATCH (n) WHERE n.age IS TYPED INT128 RETURN n",
        id="GV14_int128",
    ),
    pytest.param(
        F.GV14,
        "MATCH (n) WHERE n.age IS TYPED INTEGER128 RETURN n",
        id="GV14_integer128",
    ),
    # GV15: 256 bit unsigned integer numbers
    pytest.param(
        F.GV15,
        "MATCH (n) WHERE n.age IS TYPED UINT256 RETURN n",
        id="GV15_uint256",
    ),
    pytest.param(
        F.GV15,
        "MATCH (n) WHERE n.age IS TYPED UNSIGNED INTEGER256 RETURN n",
        id="GV15_unsigned_integer256",
    ),
    # GV16: 256 bit signed integer numbers
    pytest.param(
        F.GV16,
        "MATCH (n) WHERE n.age IS TYPED INT256 RETURN n",
        id="GV16_int256",
    ),
    pytest.param(
        F.GV16,
        "MATCH (n) WHERE n.age IS TYPED INTEGER256 RETURN n",
        id="GV16_integer256",
    ),
    # GV17: Decimal numbers
    pytest.param(
        F.GV17,
        "MATCH (n) WHERE n.age IS TYPED DECIMAL(10) RETURN n",
        id="GV17_decimal",
    ),
    pytest.param(
        F.GV17,
        "MATCH (n) WHERE n.age IS TYPED DEC(10) RETURN n",
        id="GV17_dec",
    ),
    # GV18: Small signed integer numbers
    pytest.param(
        F.GV18,
        "MATCH (n) WHERE n.age IS TYPED SMALLINT RETURN n",
        id="GV18_smallint",
    ),
    pytest.param(
        F.GV18,
        "MATCH (n) WHERE n.age IS TYPED SMALL INTEGER RETURN n",
        id="GV18_small_integer",
    ),
    # GV19: Big signed integer numbers
    pytest.param(
        F.GV19,
        "MATCH (n) WHERE n.age IS TYPED BIGINT RETURN n",
        id="GV19_bigint",
    ),
    pytest.param(
        F.GV19,
        "MATCH (n) WHERE n.age IS TYPED BIG INTEGER RETURN n",
        id="GV19_big_integer",
    ),
    # GV20: 16 bit floating point numbers
    pytest.param(
        F.GV20,
        "MATCH (n) WHERE n.age IS TYPED FLOAT16 RETURN n",
        id="GV20_float16",
    ),
    # GV21: 32 bit floating point numbers
    pytest.param(
        F.GV21,
        "MATCH (n) WHERE n.x IS TYPED FLOAT32 RETURN n",
        id="GV21_float32",
    ),
    # GV22: Specified floating point number precision
    pytest.param(
        F.GV22,
        "MATCH (n) WHERE n.x IS TYPED FLOAT(10) RETURN n",
        id="GV22_float_with_precision",
    ),
    pytest.param(
        F.GV22,
        "MATCH (n) WHERE n.x IS TYPED FLOAT(10, 2) RETURN n",
        id="GV22_float_with_precision_and_scale",
    ),
    # GV23: Floating point type name synonyms
    pytest.param(
        F.GV23,
        "MATCH (n) WHERE n.x IS TYPED REAL RETURN n",
        id="GV23_real",
    ),
    pytest.param(
        F.GV23,
        "MATCH (n) WHERE n.x IS TYPED DOUBLE RETURN n",
        id="GV23_double",
    ),
    pytest.param(
        F.GV23,
        "MATCH (n) WHERE n.x IS TYPED DOUBLE PRECISION RETURN n",
        id="GV23_double_precision",
    ),
    # GV24: 64 bit floating point numbers
    pytest.param(
        F.GV24,
        "MATCH (n) WHERE n.x IS TYPED FLOAT64 RETURN n",
        id="GV24_float64",
    ),
    # GV25: 128 bit floating point numbers
    pytest.param(
        F.GV25,
        "MATCH (n) WHERE n.x IS TYPED FLOAT128 RETURN n",
        id="GV25_float128",
    ),
    # GV26: 256 bit floating point numbers
    pytest.param(
        F.GV26,
        "MATCH (n) WHERE n.x IS TYPED FLOAT256 RETURN n",
        id="GV26_float256",
    ),
    # GV30: Specified character string minimum length
    pytest.param(
        F.GV30,
        "MATCH (n) WHERE n.x IS TYPED STRING(1, 100) RETURN n",
        id="GV30_string_min_length",
    ),
    # GV31: Specified character string maximum length
    pytest.param(
        F.GV31,
        "MATCH (n) WHERE n.x IS TYPED STRING(100) RETURN n",
        id="GV31_string_max_length",
    ),
    pytest.param(
        F.GV31,
        "MATCH (n) WHERE n.x IS TYPED VARCHAR(100) RETURN n",
        id="GV31_varchar_max_length",
    ),
    # GV32: Specified character string fixed length
    pytest.param(
        F.GV32,
        "MATCH (n) WHERE n.x IS TYPED CHAR(10) RETURN n",
        id="GV32_char_fixed_length",
    ),
    # GV35: Byte string types
    pytest.param(
        F.GV35,
        "MATCH (n) WHERE n.x IS TYPED BYTES RETURN n",
        id="GV35_bytes_type",
    ),
    pytest.param(
        F.GV35,
        'RETURN BYTE_LENGTH(X"00")',
        id="GV35_byte_length_expression",
    ),
    pytest.param(
        F.GV35,
        'RETURN OCTET_LENGTH(X"00")',
        id="GV35_octet_length_expression",
    ),
    # GV36: Specified byte string minimum length
    pytest.param(
        F.GV36,
        "MATCH (n) WHERE n.x IS TYPED BYTES(1, 100) RETURN n",
        id="GV36_bytes_min_length",
    ),
    # GV37: Specified byte string maximum length
    pytest.param(
        F.GV37,
        "MATCH (n) WHERE n.x IS TYPED BYTES(100) RETURN n",
        id="GV37_bytes_max_length",
    ),
    pytest.param(
        F.GV37,
        "MATCH (n) WHERE n.x IS TYPED VARBINARY(100) RETURN n",
        id="GV37_varbinary_max_length",
    ),
    # GV38: Specified byte string fixed length
    pytest.param(
        F.GV38,
        "MATCH (n) WHERE n.x IS TYPED BINARY(10) RETURN n",
        id="GV38_binary_fixed_length",
    ),
    # GV39: Temporal types: date, local datetime, and local time support
    pytest.param(
        F.GV39,
        "MATCH (n) WHERE n.x IS TYPED DATE RETURN n",
        id="GV39_date_type",
    ),
    pytest.param(
        F.GV39,
        "MATCH (n) WHERE n.x IS TYPED LOCAL DATETIME RETURN n",
        id="GV39_localdatetime_type",
    ),
    pytest.param(
        F.GV39,
        "MATCH (n) WHERE n.x IS TYPED LOCAL TIME RETURN n",
        id="GV39_localtime_type",
    ),
    pytest.param(
        F.GV39,
        "RETURN CURRENT_DATE",
        id="GV39_date_function",
    ),
    pytest.param(
        F.GV39,
        "RETURN DATE '2024-01-01'",
        id="GV39_temporal_literal",
    ),
    # GV40: Temporal types: zoned datetime and zoned time support
    pytest.param(
        F.GV40,
        "MATCH (n) WHERE n.x IS TYPED ZONED DATETIME RETURN n",
        id="GV40_datetime_type",
    ),
    pytest.param(
        F.GV40,
        "MATCH (n) WHERE n.x IS TYPED ZONED TIME RETURN n",
        id="GV40_time_type",
    ),
    pytest.param(
        F.GV40,
        "RETURN CURRENT_TIMESTAMP",
        id="GV40_datetime_function",
    ),
    pytest.param(
        F.GV40,
        "RETURN CURRENT_TIME",
        id="GV40_time_function",
    ),
    # GV41: Temporal types: duration support
    pytest.param(
        F.GV41,
        "MATCH (n) WHERE n.x IS TYPED DURATION(DAY TO SECOND) RETURN n",
        id="GV41_temporal_duration_type",
    ),
    pytest.param(
        F.GV41,
        "RETURN DURATION 'P1Y2M'",
        id="GV41_duration_literal",
    ),
    # GV45: Record types
    pytest.param(
        F.GV45,
        "MATCH (n) WHERE n.x IS TYPED RECORD RETURN n",
        id="GV45_record_type",
    ),
    pytest.param(
        F.GV45,
        "RETURN RECORD { name: 1 }",
        id="GV45_record_constructor",
    ),
    pytest.param(
        F.GV45,
        "RETURN { name: 1 }",
        id="GV45_record_constructor_no_keyword",
    ),
    # GV46: Closed record types
    pytest.param(
        F.GV46,
        "MATCH (n) WHERE n.x IS TYPED {name STRING} RETURN n",
        id="GV46_closed_record_type",
    ),
    pytest.param(
        F.GV46,
        "MATCH (n) WHERE n.x IS TYPED RECORD {name STRING} RETURN n",
        id="GV46_closed_record_type_with_keyword",
    ),
    # GV47: Open record types
    pytest.param(
        F.GV47,
        "MATCH (n) WHERE n.x IS TYPED ANY RECORD RETURN n",
        id="GV47_any_record_type",
    ),
    pytest.param(
        F.GV47,
        "MATCH (n) WHERE n.x IS TYPED RECORD RETURN n",
        id="GV47_record_type_plain",
    ),
    # GV48: Nested record types
    pytest.param(
        F.GV48,
        "CREATE GRAPH TYPE t { NODE TYPE :P => { f RECORD } }",
        id="GV48_property_type_with_record",
    ),
    pytest.param(
        F.GV48,
        "MATCH (n) WHERE n.x IS TYPED {inner {nested STRING}} RETURN n",
        id="GV48_field_type_with_nested_record",
    ),
    pytest.param(
        F.GV48,
        "RETURN { inner: { name: 1 } }",
        id="GV48_field_with_nested_record_constructor",
    ),
    # GV50: List value types
    pytest.param(
        F.GV50,
        "MATCH (n) WHERE n.x IS TYPED LIST<INT32> RETURN n",
        id="GV50_list_value_type",
    ),
    pytest.param(
        F.GV50,
        "RETURN [1, 2, 3]",
        id="GV50_list_literal",
    ),
    pytest.param(
        F.GV50,
        "RETURN LIST[1, 2, 3]",
        id="GV50_list_constructor_with_keyword",
    ),
    pytest.param(
        F.GV50,
        "RETURN [1] || [2]",
        id="GV50_list_concatenation",
    ),
    # GV55: Path value types
    pytest.param(
        F.GV55,
        "MATCH (n) WHERE n.x IS TYPED PATH RETURN n",
        id="GV55_path_value_type",
    ),
    pytest.param(
        F.GV55,
        "RETURN PATH [n]",
        id="GV55_path_value_expression",
    ),
    # GV60: Graph reference value types
    pytest.param(
        F.GV60,
        "MATCH (n) WHERE n.x IS TYPED ANY GRAPH RETURN n",
        id="GV60_graph_reference_value_type",
    ),
    pytest.param(
        F.GV60,
        "RETURN GRAPH my_graph",
        id="GV60_graph_reference_value_expression",
    ),
    # GV61: Binding table reference value types
    pytest.param(
        F.GV61,
        "MATCH (n) WHERE n.x IS TYPED TABLE {name STRING} RETURN n",
        id="GV61_binding_table_reference_value_type",
    ),
    pytest.param(
        F.GV61,
        "RETURN TABLE { MATCH (n) RETURN n }",
        id="GV61_binding_table_reference_value_expression",
    ),
    # GV66: Open dynamic union types
    pytest.param(
        F.GV66,
        "MATCH (n) WHERE n.x IS TYPED ANY RETURN n",
        id="GV66_open_dynamic_union_type",
    ),
    # GV67: Closed dynamic union types
    pytest.param(
        F.GV67,
        "MATCH (n) WHERE n.x IS TYPED <INT32 | STRING> RETURN n",
        id="GV67_closed_dynamic_union_type",
    ),
    # GV68: Dynamic property value types
    pytest.param(
        F.GV68,
        "MATCH (n) WHERE n.x IS TYPED PROPERTY VALUE RETURN n",
        id="GV68_dynamic_property_value_type",
    ),
    # GV71: Immaterial value types: null type support
    pytest.param(
        F.GV71,
        "MATCH (n) WHERE n.x IS TYPED NULL RETURN n",
        id="GV71_null_type",
    ),
    # GV72: Immaterial value types: empty type support
    pytest.param(
        F.GV72,
        "MATCH (n) WHERE n.x IS TYPED NOTHING RETURN n",
        id="GV72_empty_type_nothing",
    ),
    # GV90: Explicit value type nullability
    pytest.param(
        F.GV90,
        "MATCH (n) WHERE n.x IS TYPED INT32 NOT NULL RETURN n",
        id="GV90_not_null_int32",
    ),
    pytest.param(
        F.GV90,
        "MATCH (n) WHERE n.x IS TYPED STRING NOT NULL RETURN n",
        id="GV90_not_null_string",
    ),
    pytest.param(
        F.GV90,
        "MATCH (n) WHERE n.x IS TYPED BOOL NOT NULL RETURN n",
        id="GV90_not_null_bool",
    ),
    pytest.param(
        F.GV90,
        "MATCH (n) WHERE n.x IS TYPED PATH NOT NULL RETURN n",
        id="GV90_not_null_path",
    ),
    # GP18: Catalog and data statement mixing in a statement block
    pytest.param(
        F.GP18,
        "CALL { CREATE SCHEMA /s NEXT SET n.prop = 1 } RETURN 1",
        id="GP18_catalog_and_data_statement_mixing",
    ),
    # GS10: SESSION SET binding table parameters based on subqueries
    pytest.param(
        F.GS10,
        "SESSION SET TABLE $t = { MATCH (n) RETURN n }",
        id="GS10_session_set_binding_table_subquery",
    ),
    # GS11: SESSION SET value parameters based on subqueries
    pytest.param(
        F.GS11,
        "SESSION SET VALUE $v = VALUE { MATCH (n) RETURN n.prop }",
        id="GS11_session_set_value_subquery",
    ),
    # GS12: SESSION SET graph parameters based on simple expressions or references
    pytest.param(
        F.GS12,
        "SESSION SET GRAPH $g = my_graph",
        id="GS12_session_set_graph_simple_expr",
    ),
    # GS13: SESSION SET binding table parameters based on simple expressions or references
    pytest.param(
        F.GS13,
        "SESSION SET TABLE $t = my_table",
        id="GS13_session_set_binding_table_simple_expr",
    ),
    # GS14: SESSION SET value parameters based on simple expressions
    pytest.param(
        F.GS14,
        "SESSION SET VALUE $v = 42",
        id="GS14_session_set_value_simple_expr",
    ),
    # GV65: Dynamic union types
    pytest.param(
        F.GV65,
        "MATCH (n) WHERE n.x IS TYPED <INT32 | STRING> RETURN n",
        id="GV65_dynamic_union_type",
    ),
    # GV70: Immaterial value types
    pytest.param(
        F.GV70,
        "MATCH (n) WHERE n.x IS TYPED NULL RETURN n",
        id="GV70_immaterial_value_type_null",
    ),
    pytest.param(
        F.GV70,
        "MATCH (n) WHERE n.x IS TYPED NOTHING RETURN n",
        id="GV70_immaterial_value_type_empty",
    ),
    # GH01: External object references
    pytest.param(
        F.GH01,
        "CREATE PROPERTY GRAPH TYPE my_type COPY OF 'http://example.com/type'",
        id="GH01_external_object_reference",
    ),
    # GL12: SQL interval literal
    pytest.param(
        F.GL12,
        "RETURN INTERVAL '1' YEAR",
        id="GL12_sql_interval_year",
    ),
    pytest.param(
        F.GL12,
        "RETURN INTERVAL '1-6' YEAR TO MONTH",
        id="GL12_sql_interval_year_to_month",
    ),
    # GL12: SqlDatetimeLiteral is implemented but unreachable in practice because
    # DateLiteral/TimeLiteral/DatetimeLiteral are tried first in parse_temporal_literal.
    # No test case is possible since the same tokens are consumed by the earlier parsers.
    # =========================================================================
    # Core (mandatory) features
    # =========================================================================
    pytest.param(
        F.GG_SM03,
        "SESSION CLOSE",
        id="GG_SM03_session_close",
    ),
    pytest.param(
        F.GG_SM02,
        "SESSION RESET SCHEMA",
        id="GG_SM02_session_reset",
    ),
    pytest.param(
        F.GG_SM01,
        "SESSION SET SCHEMA HOME_SCHEMA",
        id="GG_SM01_session_set",
    ),
    pytest.param(
        F.GG_GE01,
        "USE CURRENT_GRAPH MATCH (n) RETURN n",
        id="GG_GE01_current_graph",
    ),
    pytest.param(
        F.GG_SC02,
        "AT HOME_SCHEMA MATCH (n) RETURN n",
        id="GG_SC02_home_schema",
    ),
    pytest.param(
        F.GG_SC03,
        "AT CURRENT_SCHEMA MATCH (n) RETURN n",
        id="GG_SC03_current_schema",
    ),
    # GG:SS01: SELECT statement
    pytest.param(
        F.GG_SS01,
        "SELECT 1",
        id="GG_SS01_select_statement",
    ),
    # GG:TL01: Temporal literals
    pytest.param(
        F.GG_TL01,
        "RETURN DATE '2024-01-15'",
        id="GG_TL01_date_literal",
    ),
    pytest.param(
        F.GG_TL01,
        "RETURN TIME '10:30:00'",
        id="GG_TL01_time_literal",
    ),
    pytest.param(
        F.GG_TL01,
        "RETURN DATETIME '2024-01-15T10:30:00+01:00'",
        id="GG_TL01_datetime_literal",
    ),
    # GG:UE01: Undirected full edge patterns (tilde forms)
    pytest.param(
        F.GG_UE01,
        "MATCH (a)~[r]~(b) RETURN a",
        id="GG_UE01_full_edge_undirected",
    ),
    # GG:UE02: Undirected abbreviated edge patterns (tilde forms)
    pytest.param(
        F.GG_UE02,
        "MATCH (a)~(b) RETURN a",
        id="GG_UE02_abbreviated_tilde",
    ),
]


def build_dialect_without_feature(feature: Feature) -> Dialect:
    """Return a Dialect instance with a specific feature disabled."""
    supported = ALL_FEATURES - {feature}

    class RestrictedDialect(Dialect):
        SUPPORTED_FEATURES = supported

    return RestrictedDialect()


@pytest.fixture(scope="module")
def full_dialect() -> Dialect:
    """Shared full dialect instance."""
    return Dialect()


@pytest.mark.parametrize(("feature", "query"), TEST_CASES)
def test_supported_feature_parses_successfully(full_dialect: Dialect, feature: Feature, query: str):
    result = full_dialect.parse(query)
    assert result, "Expected non-empty parse result"


@pytest.mark.parametrize(("feature", "query"), TEST_CASES)
def test_unsupported_feature_raises_error(feature: Feature, query: str):
    dialect = build_dialect_without_feature(feature)

    with pytest.raises(FeatureError) as exc:
        dialect.parse(query)

    message = str(exc.value)
    assert str(feature) in message
    assert "not supported" in message


# Per ISO/IEC 39075:2024 §16.7: Without G043, conforming GQL language shall
# not contain a <full edge pattern> that is not a <full edge any direction>,
# a <full edge pointing left>, or a <full edge pointing right>.
# These three are mandatory and must parse WITHOUT G043.
G043_MANDATORY_FORMS = [
    pytest.param(
        "MATCH (a)<-[r]-(b) RETURN a",
        id="full_edge_pointing_left_is_mandatory",
    ),
    pytest.param(
        "MATCH (a)-[r]-(b) RETURN a",
        id="full_edge_any_direction_is_mandatory",
    ),
    pytest.param(
        "MATCH (a)-[r]->(b) RETURN a",
        id="full_edge_pointing_right_is_mandatory",
    ),
]


@pytest.mark.parametrize("query", G043_MANDATORY_FORMS)
def test_mandatory_full_edge_patterns_parse_without_g043(query: str):
    """FullEdgePointingLeft, FullEdgeAnyDirection, and FullEdgePointingRight
    are mandatory forms that must not require G043."""
    dialect = build_dialect_without_feature(F.G043)
    result = dialect.parse(query)
    assert result, f"Mandatory full edge pattern should parse without G043: {query}"


def test_select_does_not_require_gq01():
    """SELECT is routed through FocusedLinearQueryStatement by the grammar,
    but should not require GQ01 (USE graph clause)."""
    dialect = build_dialect_without_feature(F.GQ01)
    result = dialect.parse("SELECT 1 AS test")
    assert result, "SELECT should parse without GQ01"


# GG:UE01 gates the 3 undirected full edge forms (tilde variants of G043).
# GG:UE02 gates the 3 undirected abbreviated edge forms (tilde variants of G045).
# Neo4j doesn't support these because all its edges are directed.
GG_UE01_CASES = [
    pytest.param(
        "MATCH (a)~[r]~(b) RETURN a",
        id="full_edge_undirected",
    ),
    pytest.param(
        "MATCH (a)<~[r]~(b) RETURN a",
        id="full_edge_left_or_undirected",
    ),
    pytest.param(
        "MATCH (a)~[r]~>(b) RETURN a",
        id="full_edge_undirected_or_right",
    ),
]

GG_UE02_CASES = [
    pytest.param(
        "MATCH (a)~(b) RETURN a",
        id="abbreviated_tilde",
    ),
    pytest.param(
        "MATCH (a)<~(b) RETURN a",
        id="abbreviated_left_arrow_tilde",
    ),
    pytest.param(
        "MATCH (a)~>(b) RETURN a",
        id="abbreviated_tilde_right_arrow",
    ),
]


@pytest.mark.parametrize("query", GG_UE01_CASES)
def test_undirected_full_edge_requires_gg_ue01(query: str):
    """Undirected full edge forms require GG:UE01."""
    dialect = build_dialect_without_feature(F.GG_UE01)
    with pytest.raises(FeatureError) as exc:
        dialect.parse(query)
    assert "GG:UE01" in str(exc.value)


@pytest.mark.parametrize("query", GG_UE02_CASES)
def test_undirected_abbreviated_edge_requires_gg_ue02(query: str):
    """Undirected abbreviated edge forms require GG:UE02."""
    dialect = build_dialect_without_feature(F.GG_UE02)
    with pytest.raises(FeatureError) as exc:
        dialect.parse(query)
    assert "GG:UE02" in str(exc.value)
