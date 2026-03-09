"""
Get Test Queries Tool - 获取标准测试查询集

返回用于内存检索评估的标准测试查询集，包含不同类别和难度的查询。
"""

TOOL_SCHEMA = {
    "name": "get_test_queries",
    "description": "Get the standardized test query set for memory retrieval benchmarking. "
    "Queries are stratified by category (semantic, episodic, procedural, strategic) "
    "and difficulty (easy, medium, hard). Use this to understand what queries the benchmark uses.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "description": "Filter by category: semantic, episodic, procedural, strategic",
            },
            "difficulty": {
                "type": "string",
                "description": "Filter by difficulty: easy, medium, hard",
            },
            "limit": {
                "type": "integer",
                "default": 30,
                "description": "Maximum number of queries to return",
            },
        },
    },
}

TEST_QUERIES = [
    {
        "id": "T01",
        "query": "What preferences does the user have for their home setup?",
        "category": "semantic",
        "difficulty": "easy",
    },
    {
        "id": "T02",
        "query": "What happened during the last consolidation cycle?",
        "category": "episodic",
        "difficulty": "medium",
    },
    {
        "id": "T03",
        "query": "How should I handle sensitive data when sharing between agents?",
        "category": "procedural",
        "difficulty": "medium",
    },
    {
        "id": "T04",
        "query": "recurring patterns in project planning failures",
        "category": "strategic",
        "difficulty": "hard",
    },
    {
        "id": "T05",
        "query": "What tools were configured for audio processing?",
        "category": "semantic",
        "difficulty": "easy",
    },
    {
        "id": "T06",
        "query": "emotional context of recent family discussions",
        "category": "episodic",
        "difficulty": "hard",
    },
    {
        "id": "T07",
        "query": "steps to deploy a new version safely",
        "category": "procedural",
        "difficulty": "medium",
    },
    {
        "id": "T08",
        "query": "user's coding style preferences",
        "category": "semantic",
        "difficulty": "easy",
    },
    {
        "id": "T09",
        "query": "what was discussed in the last team meeting",
        "category": "episodic",
        "difficulty": "medium",
    },
    {
        "id": "T10",
        "query": "best practices for error handling",
        "category": "procedural",
        "difficulty": "easy",
    },
    {
        "id": "T11",
        "query": "Why did the previous API integration fail?",
        "category": "episodic",
        "difficulty": "hard",
    },
    {
        "id": "T12",
        "query": "what is the user's preferred communication style",
        "category": "semantic",
        "difficulty": "easy",
    },
    {
        "id": "T13",
        "query": "instructions for setting up the development environment",
        "category": "procedural",
        "difficulty": "easy",
    },
    {
        "id": "T14",
        "query": "long-term strategy for technical debt reduction",
        "category": "strategic",
        "difficulty": "hard",
    },
    {
        "id": "T15",
        "query": "user's preferences for code review feedback",
        "category": "semantic",
        "difficulty": "medium",
    },
    {
        "id": "T16",
        "query": "details of the last database migration",
        "category": "episodic",
        "difficulty": "medium",
    },
    {
        "id": "T17",
        "query": "how to run the test suite",
        "category": "procedural",
        "difficulty": "easy",
    },
    {
        "id": "T18",
        "query": "patterns in successful product launches",
        "category": "strategic",
        "difficulty": "hard",
    },
    {
        "id": "T19",
        "query": "user's pet peeves in code reviews",
        "category": "semantic",
        "difficulty": "medium",
    },
    {
        "id": "T20",
        "query": "what went wrong in the incident last week",
        "category": "episodic",
        "difficulty": "hard",
    },
    {
        "id": "T21",
        "query": "process for requesting time off",
        "category": "procedural",
        "difficulty": "easy",
    },
    {
        "id": "T22",
        "query": "lessons from past project failures",
        "category": "strategic",
        "difficulty": "hard",
    },
    {
        "id": "T23",
        "query": "what does the user like to work on",
        "category": "semantic",
        "difficulty": "easy",
    },
    {
        "id": "T24",
        "query": "context of previous customer negotiations",
        "category": "episodic",
        "difficulty": "hard",
    },
    {
        "id": "T25",
        "query": "how to provision new cloud resources",
        "category": "procedural",
        "difficulty": "medium",
    },
    {
        "id": "T26",
        "query": "what was the user's goal for this project",
        "category": "semantic",
        "difficulty": "medium",
    },
    {
        "id": "T27",
        "query": "history of system outages and root causes",
        "category": "episodic",
        "difficulty": "hard",
    },
    {
        "id": "T28",
        "query": "onboarding process for new team members",
        "category": "procedural",
        "difficulty": "easy",
    },
    {
        "id": "T29",
        "query": "key performance indicators for the team",
        "category": "strategic",
        "difficulty": "medium",
    },
    {
        "id": "T30",
        "query": "user's working hours and availability",
        "category": "semantic",
        "difficulty": "easy",
    },
]


def execute(category: str = None, difficulty: str = None, limit: int = 30) -> str:
    """
    获取标准测试查询集

    Args:
        category: 按类别过滤（semantic, episodic, procedural, strategic）
        difficulty: 按难度过滤（easy, medium, hard）
        limit: 返回的最大数量

    Returns:
        格式化的测试查询列表
    """
    queries = TEST_QUERIES

    if category:
        queries = [q for q in queries if q["category"] == category]

    if difficulty:
        queries = [q for q in queries if q["difficulty"] == difficulty]

    queries = queries[:limit]

    output = "## Memory Benchmark Test Queries\n\n"
    output += f"**Total queries**: {len(queries)}"
    if category:
        output += f" (category: {category})"
    if difficulty:
        output += f" (difficulty: {difficulty})"
    output += "\n\n"

    by_category = {}
    for q in queries:
        cat = q["category"]
        if cat not in by_category:
            by_category[cat] = {"easy": 0, "medium": 0, "hard": 0}
        by_category[cat][q["difficulty"]] += 1

    output += "### Distribution by Category and Difficulty\n\n"
    output += "| Category | Easy | Medium | Hard |\n"
    output += "|----------|------|--------|------|\n"
    for cat in ["semantic", "episodic", "procedural", "strategic"]:
        if cat in by_category:
            d = by_category[cat]
            output += f"| {cat} | {d['easy']} | {d['medium']} | {d['hard']} |\n"
    output += "\n"

    output += "### Query List\n\n"
    output += "| ID | Category | Difficulty | Query |\n"
    output += "|----|----------|------------|-------|\n"

    for q in queries:
        query_short = q["query"][:60] + "..." if len(q["query"]) > 60 else q["query"]
        output += f"| {q['id']} | {q['category']} | {q['difficulty']} | {query_short} |\n"

    output += "\n---\n"
    output += "*Use `run_memory_assessment` tool to run these queries against the memory system.*"

    return output


if __name__ == "__main__":
    print(execute())
