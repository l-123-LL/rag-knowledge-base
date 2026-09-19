"""拒答阈值标定的纯逻辑测试（不下载模型）。"""

from evaluation.calibrate_threshold import coverage, pick_threshold


def test_pick_threshold_returns_midpoint_when_separable() -> None:
    result = pick_threshold([0.55, 0.43, 0.61], [0.36, 0.12])

    assert result["separable"] is True
    assert result["relevant_min"] == 0.43
    assert result["unrelated_max"] == 0.36
    assert result["threshold"] == 0.395


def test_pick_threshold_refuses_when_groups_overlap() -> None:
    # 两组重叠时必须说"分不开"，而不是硬给一个看起来能用的数字
    result = pick_threshold([0.40, 0.62], [0.45, 0.30])

    assert result["separable"] is False
    assert result["threshold"] is None


def test_coverage_counts_kept_and_blocked() -> None:
    result = coverage(0.40, [0.55, 0.39, 0.41], [0.36, 0.44])

    assert result == {
        "kept": 2,
        "kept_total": 3,
        "blocked": 1,
        "blocked_total": 2,
    }
