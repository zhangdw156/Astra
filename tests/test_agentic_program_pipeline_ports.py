from __future__ import annotations

import importlib.util
import socket
from pathlib import Path


def load_module():
    module_path = (
        Path(__file__).resolve().parents[1]
        / "exps"
        / "data_synthesis_workflow"
        / "pipeline4_selected_skills_agentic.py"
    )
    spec = importlib.util.spec_from_file_location(
        "pipeline4_selected_skills_agentic", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_allocate_ports_skips_occupied_port() -> None:
    module = load_module()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    occupied_port = sock.getsockname()[1]

    try:
        ports = module.allocate_ports(count=2, base_port=occupied_port)
        assert occupied_port not in ports
        assert len(ports) == 2
        assert len(set(ports)) == 2
    finally:
        sock.close()
