import numpy as np
import pytest

from scientific_parallax.protocol.dry_run import gray_scott_ir
from scientific_parallax.protocol.paradigm_ir import (
    LawTerm,
    ParadigmIR,
    equivalent_under_declared_transforms,
)


def test_variable_renaming_is_same_equivalence_class() -> None:
    first = gray_scott_ir("a")
    renamed = gray_scott_ir("b", "x", "y")
    signature = np.asarray([1.0, 2.0, 3.0])
    assert equivalent_under_declared_transforms(first, renamed, signature, signature)


def test_equal_syntax_with_different_intervention_behavior_is_not_equivalent() -> None:
    first = gray_scott_ir("a")
    second = gray_scott_ir("b", "x", "y")
    assert not equivalent_under_declared_transforms(first, second, [1.0], [2.0])


def test_undeclared_variable_is_rejected() -> None:
    base = gray_scott_ir("bad")
    bad = ParadigmIR(
        base.paradigm_id,
        base.variables,
        (*base.terms, LawTerm("missing", "source", ("missing",), "c")),
        base.measurement,
        base.scope,
    )
    with pytest.raises(ValueError, match="undeclared"):
        bad.validate()
