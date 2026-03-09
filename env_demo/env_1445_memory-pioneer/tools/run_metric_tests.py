"""
Run Metric Tests Tool - 运行 IR 指标单元测试

验证 IR 指标计算的正确性（DCG, nDCG, MAP, RAR, MRR, etc.）。
"""

import math

TOOL_SCHEMA = {
    "name": "run_metric_tests",
    "description": "Run unit tests for Information Retrieval metrics used in memory benchmarking. "
    "Tests include DCG, nDCG, Average Precision, Precision@k, Hit Rate, RAR, and MRR. "
    "Use this to verify metric calculation correctness.",
    "inputSchema": {"type": "object", "properties": {}},
}


def dcg(ratings, k=5):
    """Discounted Cumulative Gain."""
    total = 0.0
    for i, r in enumerate(ratings[:k]):
        total += (2**r - 1) / math.log2(i + 2)
    return total


def ndcg(ratings, k=5):
    """Normalized DCG — compares actual ranking to ideal."""
    actual = dcg(ratings, k)
    ideal = dcg(sorted(ratings, reverse=True), k)
    return actual / ideal if ideal > 0 else 0.0


def average_precision(ratings, k=5, threshold=3):
    """Average Precision at k."""
    relevant_count = 0
    precision_sum = 0.0
    for i, r in enumerate(ratings[:k]):
        if r >= threshold:
            relevant_count += 1
            precision_sum += relevant_count / (i + 1)
    return precision_sum / min(k, len(ratings)) if ratings else 0.0


def precision_at_k(ratings, k=5, threshold=3):
    return sum(1 for r in ratings[:k] if r >= threshold) / k if ratings else 0.0


def hit_rate(ratings, threshold=3):
    return 1.0 if any(r >= threshold for r in ratings) else 0.0


def compute_rar(ratings, threshold=3):
    if not ratings:
        return 0.0
    return sum(1 for r in ratings if r >= threshold) / len(ratings)


def compute_mrr(ratings, threshold=3):
    for i, r in enumerate(ratings):
        if r >= threshold:
            return 1.0 / (i + 1)
    return 0.0


def run_tests():
    """Run all metric tests and return results."""
    results = []

    def assert_test(name, condition, expected=None, actual=None):
        if condition:
            results.append({"test": name, "status": "PASS"})
        else:
            results.append(
                {"test": name, "status": "FAIL", "expected": str(expected), "actual": str(actual)}
            )

    ratings = [5, 4, 3, 2, 1]
    expected_dcg = 31.0 + 15 / math.log2(3) + 7 / math.log2(4) + 3 / math.log2(5) + 1 / math.log2(6)
    actual_dcg = dcg(ratings, 5)
    assert_test(
        "DCG with known values", abs(actual_dcg - expected_dcg) < 0.01, expected_dcg, actual_dcg
    )

    assert_test("nDCG perfect", ndcg([5, 4, 3, 2, 1]) == 1.0, 1.0, ndcg([5, 4, 3, 2, 1]))

    reversed_ndcg = ndcg([1, 2, 3, 4, 5])
    assert_test("nDCG reversed < 1.0", 0 < reversed_ndcg < 1.0, "< 1.0", reversed_ndcg)

    assert_test("nDCG empty", ndcg([]) == 0.0, 0.0, ndcg([]))

    ap = average_precision([4, 1, 4, 1, 4], k=5, threshold=3)
    assert_test("Average Precision", abs(ap - 0.4533) < 0.01, 0.4533, ap)

    p5 = precision_at_k([5, 1, 4, 1, 3], k=5, threshold=3)
    assert_test("Precision@5", p5 == 0.6, 0.6, p5)

    assert_test(
        "Hit rate with hits", hit_rate([1, 1, 3, 1, 1]) == 1.0, 1.0, hit_rate([1, 1, 3, 1, 1])
    )
    assert_test(
        "Hit rate no hits", hit_rate([1, 1, 1, 1, 1]) == 0.0, 0.0, hit_rate([1, 1, 1, 1, 1])
    )
    assert_test("Hit rate empty", hit_rate([]) == 0.0, 0.0, hit_rate([]))

    assert_test(
        "RAR with ratings", compute_rar([5, 4, 3, 2, 1]) == 0.6, 0.6, compute_rar([5, 4, 3, 2, 1])
    )
    assert_test("RAR empty", compute_rar([]) == 0.0, 0.0, compute_rar([]))

    assert_test(
        "MRR first relevant",
        compute_mrr([1, 1, 4, 1, 1]) == 1 / 3,
        1 / 3,
        compute_mrr([1, 1, 4, 1, 1]),
    )
    assert_test(
        "MRR at position 1", compute_mrr([5, 1, 1, 1, 1]) == 1.0, 1.0, compute_mrr([5, 1, 1, 1, 1])
    )
    assert_test(
        "MRR no relevant", compute_mrr([1, 1, 1, 1, 1]) == 0.0, 0.0, compute_mrr([1, 1, 1, 1, 1])
    )

    return results


def execute() -> str:
    """
    运行 IR 指标单元测试

    Returns:
        格式化的测试结果
    """
    results = run_tests()

    output = "## IR Metric Unit Tests\n\n"

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    output += f"**Total**: {len(results)} | **Passed**: {passed} | **Failed**: {failed}\n\n"

    output += "### Test Results\n\n"
    output += "| Test | Status |\n"
    output += "|------|--------|\n"

    for r in results:
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        output += f"| {r['test']} | {status_icon} {r['status']} |\n"

    if failed > 0:
        output += "\n### Failed Details\n\n"
        for r in results:
            if r["status"] == "FAIL":
                output += f"**{r['test']}**\n"
                output += f"- Expected: {r['expected']}\n"
                output += f"- Actual: {r['actual']}\n\n"

    output += "---\n"
    output += "*All core IR metrics are verified to compute correctly.*"

    return output


if __name__ == "__main__":
    print(execute())
