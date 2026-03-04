# 单元测试：astra.scripts.update_gitmodules 中的 URL 解析、.gitmodules 读写与配置加载

import tempfile
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from astra.scripts.update_gitmodules import (
    load_repos_from_config,
    normalize_url,
    parse_github_url,
    parse_gitmodules,
    submodule_path_rel,
    write_gitmodules,
)


class TestNormalizeUrl:
    def test_strips_whitespace(self) -> None:
        assert normalize_url("  https://github.com/a/b  ") == "https://github.com/a/b"

    def test_removes_dot_git(self) -> None:
        assert normalize_url("https://github.com/a/b.git") == "https://github.com/a/b"

    def test_removes_trailing_slash(self) -> None:
        assert normalize_url("https://github.com/a/b/") == "https://github.com/a/b"


class TestParseGithubUrl:
    def test_https_owner_repo(self) -> None:
        assert parse_github_url("https://github.com/owner/repo") == ("owner", "repo")

    def test_http_and_dot_git(self) -> None:
        assert parse_github_url("http://github.com/foo/bar.git") == ("foo", "bar")

    def test_trailing_slash(self) -> None:
        assert parse_github_url("https://github.com/a/b/") == ("a", "b")

    def test_non_github_returns_none(self) -> None:
        assert parse_github_url("https://gitlab.com/a/b") is None
        assert parse_github_url("https://example.com/a/b") is None

    def test_invalid_path_returns_none(self) -> None:
        assert parse_github_url("https://github.com/onlyone") is None


class TestSubmodulePathRel:
    def test_format(self) -> None:
        assert submodule_path_rel("owner", "repo") == "skillshub/owner_repo"


class TestParseGitmodules:
    def test_missing_file_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            assert parse_gitmodules(Path(d) / "nonexistent") == []

    def test_single_submodule(self) -> None:
        content = '''[submodule "skillshub/foo_bar"]
\tpath = skillshub/foo_bar
\turl = https://github.com/foo/bar
'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".gitmodules", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)
        try:
            got = parse_gitmodules(path)
            assert len(got) == 1
            name, sub_path, url, ignore = got[0]
            assert name == "skillshub/foo_bar"
            assert sub_path == "skillshub/foo_bar"
            assert url == "https://github.com/foo/bar"
            assert ignore is None
        finally:
            path.unlink()

    def test_submodule_with_ignore(self) -> None:
        content = '''[submodule "skillshub/a_b"]
\tpath = skillshub/a_b
\turl = https://github.com/a/b
\tignore = dirty
'''
        with tempfile.NamedTemporaryFile(mode="w", suffix=".gitmodules", delete=False) as f:
            f.write(content)
            f.flush()
            path = Path(f.name)
        try:
            got = parse_gitmodules(path)
            assert len(got) == 1
            _, _, _, ignore = got[0]
            assert ignore == "dirty"
        finally:
            path.unlink()


class TestWriteGitmodules:
    def test_roundtrip_with_parse(self) -> None:
        entries = [
            ("skillshub/a_b", "skillshub/a_b", "https://github.com/a/b", None),
            ("skillshub/c_d", "skillshub/c_d", "https://github.com/c/d", "dirty"),
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".gitmodules", delete=False) as f:
            path = Path(f.name)
        try:
            write_gitmodules(path, entries)
            got = parse_gitmodules(path)
            assert got == entries
        finally:
            path.unlink()


class TestLoadReposFromConfig:
    def test_repos_key(self) -> None:
        conf = OmegaConf.create({"repos": ["https://github.com/a/b", "https://github.com/c/d"]})
        assert load_repos_from_config(conf) == [
            "https://github.com/a/b",
            "https://github.com/c/d",
        ]

    def test_repositories_key(self) -> None:
        conf = OmegaConf.create({"repositories": ["https://github.com/x/y"]})
        assert load_repos_from_config(conf) == ["https://github.com/x/y"]

    def test_top_level_list(self) -> None:
        conf = OmegaConf.create(["https://github.com/p/q"])
        assert load_repos_from_config(conf) == ["https://github.com/p/q"]

    def test_none_returns_empty(self) -> None:
        assert load_repos_from_config(None) == []

    def test_empty_or_no_list_returns_empty(self) -> None:
        assert load_repos_from_config(OmegaConf.create({})) == []
        assert load_repos_from_config(OmegaConf.create({"repos": []})) == []
