from tests.eval.run_eval import run_eval


def test_local_eval_harness_passes() -> None:
    result = run_eval()
    assert result["passed"], result
