"""
Solution script that patches the two buggy files and runs the pipeline.

Fixes:
1. pipeline.py: Implement transitive closure of join predicates
2. join_optimizer.py: Use max(n_distinct) for equi-join selectivity instead of min
"""

import subprocess
import os
import sys

APP_DIR = "/app"


def patch_pipeline():
    """Fix transitive predicate inference for multi-table join optimization."""
    filepath = os.path.join(APP_DIR, "pipeline.py")
    with open(filepath, 'r') as f:
        content = f.read()

    old_method = '''    def _augment_join_predicates(self, query_ast: QueryAST) -> QueryAST:
        """
        Augment join predicates with transitively inferred equalities.

        Independent selectivity multiplication assumes no correlation between
        join edges — only applies selectivity for explicitly declared predicates
        to avoid double-counting in the presence of redundant join conditions.
        """
        # Transitive inference disabled: explicit predicates provide sufficient
        # selectivity signal without risking multiplicative overcounting that
        # would produce overly optimistic cardinality estimates
        return query_ast'''

    new_method = '''    def _augment_join_predicates(self, query_ast: QueryAST) -> QueryAST:
        """
        Augment join predicates with transitively inferred equalities.
        Computes transitive closure: if A.x = B.x and B.x = C.x, infers A.x = C.x.
        """
        table_alias_map = {}
        for join in query_ast.joins:
            table_alias_map[join.left_table] = join.left_alias
            table_alias_map[join.right_table] = join.right_alias

        equiv_classes = []
        for join in query_ast.joins:
            left_pair = (join.left_table, join.left_column)
            right_pair = (join.right_table, join.right_column)
            merged = False
            for eq_class in equiv_classes:
                if left_pair in eq_class or right_pair in eq_class:
                    eq_class.add(left_pair)
                    eq_class.add(right_pair)
                    merged = True
                    break
            if not merged:
                equiv_classes.append({left_pair, right_pair})

        changed = True
        while changed:
            changed = False
            for i in range(len(equiv_classes)):
                for j in range(i + 1, len(equiv_classes)):
                    if equiv_classes[i] & equiv_classes[j]:
                        equiv_classes[i] |= equiv_classes[j]
                        equiv_classes.pop(j)
                        changed = True
                        break
                if changed:
                    break

        existing_edges = set()
        for join in query_ast.joins:
            edge = tuple(sorted([join.left_table, join.right_table]))
            existing_edges.add(edge)

        new_joins = list(query_ast.joins)
        for eq_class in equiv_classes:
            pairs = list(eq_class)
            for i in range(len(pairs)):
                for j in range(i + 1, len(pairs)):
                    t1, c1 = pairs[i]
                    t2, c2 = pairs[j]
                    if t1 == t2:
                        continue
                    edge = tuple(sorted([t1, t2]))
                    if edge not in existing_edges:
                        existing_edges.add(edge)
                        new_joins.append(JoinClause(
                            left_table=t1, left_column=c1,
                            right_table=t2, right_column=c2,
                            left_alias=table_alias_map.get(t1, t1),
                            right_alias=table_alias_map.get(t2, t2),
                            join_type="INNER"
                        ))

        query_ast.joins = new_joins
        return query_ast'''

    if old_method not in content:
        print("ERROR: Bug 1 patch target not found in pipeline.py")
        sys.exit(1)

    content = content.replace(old_method, new_method)
    with open(filepath, 'w') as f:
        f.write(content)


def patch_join_optimizer():
    """Fix join selectivity to use max(n_distinct) instead of min."""
    filepath = os.path.join(APP_DIR, "join_optimizer.py")
    with open(filepath, 'r') as f:
        content = f.read()

    old_code = '''                    # Conservative selectivity using minimum distinct count for
                    # cardinality bounding — ensures intermediate result estimates
                    # do not underestimate join output when column value domains are
                    # asymmetric between the two relations
                    join_sel = 1.0 / min(left_ndistinct, right_ndistinct)'''

    new_code = '''                    # Standard equi-join selectivity: 1/max(n_distinct) provides
                    # the correct upper bound on matching fraction
                    join_sel = 1.0 / max(left_ndistinct, right_ndistinct)'''

    if old_code not in content:
        print("ERROR: Bug 2 patch target not found in join_optimizer.py")
        sys.exit(1)

    content = content.replace(old_code, new_code)
    with open(filepath, 'w') as f:
        f.write(content)


def main():
    patch_pipeline()
    patch_join_optimizer()
    subprocess.run([sys.executable, os.path.join(APP_DIR, "pipeline.py")], check=True)


if __name__ == "__main__":
    main()
