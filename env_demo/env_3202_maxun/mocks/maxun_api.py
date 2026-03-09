"""
Maxun API Mock - 模拟 Maxun 预测市场API

Maxun 是一个网页爬虫平台，提供机器人来自动爬取网站数据。
"""

from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Header, Query
from pydantic import BaseModel
import random
from datetime import datetime, timedelta

app = FastAPI(title="Maxun Mock API")

API_KEY = "mock-api-key"


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        return False
    return True


class RobotMeta(BaseModel):
    id: str
    name: str
    type: str
    url: str


class Robot(BaseModel):
    id: str
    recording_meta: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None


class Run(BaseModel):
    runId: str
    status: str
    startedAt: str
    finishedAt: Optional[str] = None
    serializableOutput: Optional[Dict[str, Any]] = None


MOCK_ROBOTS = [
    {
        "id": "robot-001",
        "recording_meta": {
            "id": "robot-001",
            "name": "Product Scraper",
            "type": "product",
            "url": "https://example.com/products",
        },
        "config": {"scrollCount": 5, "waitFor": 2000},
    },
    {
        "id": "robot-002",
        "recording_meta": {
            "id": "robot-002",
            "name": "News Aggregator",
            "type": "news",
            "url": "https://example.com/news",
        },
        "config": {"scrollCount": 3, "waitFor": 1500},
    },
    {
        "id": "robot-003",
        "recording_meta": {
            "id": "robot-003",
            "name": "Job Listings",
            "type": "list",
            "url": "https://example.com/jobs",
        },
        "config": {"scrollCount": 10, "waitFor": 1000},
    },
    {
        "id": "robot-004",
        "recording_meta": {
            "id": "robot-004",
            "name": "Crypto Prices",
            "type": "data",
            "url": "https://example.com/crypto",
        },
        "config": {"refreshInterval": 60},
    },
]


def generate_run_result(robot_id: str, run_id: str, status: str = "completed"):
    base_time = datetime.now() - timedelta(hours=random.randint(1, 48))

    output_types = ["textData", "listData", "crawlData", "searchData"]
    output_type = random.choice(output_types)

    serializable_output = {}

    if output_type == "textData":
        serializable_output = {
            "textData": {
                "title": f"Scraped data from {robot_id}",
                "content": "This is sample scraped text content from the website.",
                "timestamp": base_time.isoformat(),
            }
        }
    elif output_type == "listData":
        serializable_output = {
            "listData": [
                {"id": 1, "name": "Item 1", "price": 10.99},
                {"id": 2, "name": "Item 2", "price": 20.99},
                {"id": 3, "name": "Item 3", "price": 15.99},
                {"id": 4, "name": "Item 4", "price": 25.99},
                {"id": 5, "name": "Item 5", "price": 30.99},
            ]
        }
    elif output_type == "crawlData":
        serializable_output = {
            "crawlData": [
                {"url": "https://example.com/page1", "title": "Page 1", "content": "Content 1"},
                {"url": "https://example.com/page2", "title": "Page 2", "content": "Content 2"},
                {"url": "https://example.com/page3", "title": "Page 3", "content": "Content 3"},
            ]
        }
    else:
        serializable_output = {
            "searchData": {
                "query": "search term",
                "results": [
                    {"title": "Result 1", "url": "https://example.com/1"},
                    {"title": "Result 2", "url": "https://example.com/2"},
                ],
            }
        }

    finished_at = (
        (base_time + timedelta(minutes=random.randint(1, 10))).isoformat()
        if status == "completed"
        else None
    )

    return {
        "runId": run_id,
        "status": status,
        "startedAt": base_time.isoformat(),
        "finishedAt": finished_at,
        "serializableOutput": serializable_output,
    }


MOCK_RUNS: Dict[str, List[Dict]] = {}


@app.get("/api/sdk/robots")
async def list_robots(
    x_api_key: str = Header(...), limit: int = Query(10, description="Max results")
):
    """列出所有机器人"""
    if x_api_key != API_KEY:
        return {"error": "Invalid API key"}, 401

    return {"data": MOCK_ROBOTS[:limit], "total": len(MOCK_ROBOTS)}


@app.get("/api/sdk/robots/{robot_id}")
async def get_robot(robot_id: str, x_api_key: str = Header(...)):
    """获取机器人详情"""
    if x_api_key != API_KEY:
        return {"error": "Invalid API key"}, 401

    for robot in MOCK_ROBOTS:
        if robot["id"] == robot_id:
            return {"data": robot}

    return {"error": "Robot not found"}, 404


@app.post("/api/sdk/robots/{robot_id}/execute")
async def execute_robot(robot_id: str, x_api_key: str = Header(...)):
    """执行机器人"""
    if x_api_key != API_KEY:
        return {"error": "Invalid API key"}, 401

    for robot in MOCK_ROBOTS:
        if robot["id"] == robot_id:
            run_id = f"run-{robot_id}-{random.randint(1000, 9999)}"
            result = {
                "runId": run_id,
                "status": "completed",
                "data": {
                    "textData": {
                        "title": f"Data from {robot['recording_meta']['name']}",
                        "content": "Successfully scraped data from target website.",
                    },
                    "listData": [
                        {"name": "Item 1", "value": 100},
                        {"name": "Item 2", "value": 200},
                    ],
                },
            }

            if robot_id not in MOCK_RUNS:
                MOCK_RUNS[robot_id] = []
            MOCK_RUNS[robot_id].append(generate_run_result(robot_id, run_id, "completed"))

            return {"data": result}

    return {"error": "Robot not found"}, 404


@app.get("/api/sdk/robots/{robot_id}/runs")
async def list_runs(robot_id: str, x_api_key: str = Header(...)):
    """列出机器人的所有运行记录"""
    if x_api_key != API_KEY:
        return {"error": "Invalid API key"}, 401

    if robot_id not in MOCK_RUNS:
        MOCK_RUNS[robot_id] = [
            generate_run_result(
                robot_id, f"run-{robot_id}-{i}", "completed" if i < 2 else "running"
            )
            for i in range(1, 4)
        ]

    return {"data": MOCK_RUNS[robot_id]}


@app.get("/api/sdk/robots/{robot_id}/runs/{run_id}")
async def get_run(robot_id: str, run_id: str, x_api_key: str = Header(...)):
    """获取运行结果"""
    if x_api_key != API_KEY:
        return {"error": "Invalid API key"}, 401

    if robot_id in MOCK_RUNS:
        for run in MOCK_RUNS[robot_id]:
            if run["runId"] == run_id:
                return {"data": run}

    return {"data": generate_run_result(robot_id, run_id, "completed")}


@app.post("/api/sdk/robots/{robot_id}/runs/{run_id}/abort")
async def abort_run(robot_id: str, run_id: str, x_api_key: str = Header(...)):
    """中止运行"""
    if x_api_key != API_KEY:
        return {"error": "Invalid API key"}, 401

    return {"data": {"success": True, "message": f"Run {run_id} aborted successfully"}}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
