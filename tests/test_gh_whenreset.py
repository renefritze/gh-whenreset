import io
import json
import re
import sys
from datetime import datetime
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest
from zoneinfo import ZoneInfo


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "gh-whenreset"


def load_script_module():
    loader = SourceFileLoader("gh_whenreset_script", str(SCRIPT_PATH))
    spec = spec_from_loader(loader.name, loader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return load_script_module()


def test_parser_defaults_and_flags(mod):
    args = mod.build_parser().parse_args([])
    assert args.all is False
    assert args.tz is None

    args = mod.build_parser().parse_args(["--all", "--tz", "UTC"])
    assert args.all is True
    assert args.tz == "UTC"


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (59, "in 59s"),
        (60, "in 1min"),
        (3599, "in 59min"),
        (3600, "in 1h"),
        (86400, "in 1d"),
        (-45, "45s ago"),
        (-7200, "2h ago"),
    ],
)
def test_format_relative(mod, seconds, expected):
    assert mod.format_relative(seconds) == expected


def test_considered_buckets_default_filters_exhausted(mod):
    resources = {
        "core": {"remaining": 0, "reset": 100},
        "search": {"remaining": 1, "reset": 200},
        "graphql": {"remaining": 0, "reset": 150},
        "invalid_type": "nope",
        "invalid_shape": {"remaining": "0", "reset": 300},
    }
    assert list(mod.considered_buckets(resources, include_all=False)) == [
        ("core", 100),
        ("graphql", 150),
    ]


def test_considered_buckets_all_includes_all_valid(mod):
    resources = {
        "core": {"remaining": 0, "reset": 100},
        "search": {"remaining": 1, "reset": 200},
        "graphql": {"remaining": 2, "reset": 150},
    }
    assert list(mod.considered_buckets(resources, include_all=True)) == [
        ("core", 100),
        ("search", 200),
        ("graphql", 150),
    ]


def test_load_input_valid_json_object(mod, monkeypatch):
    payload = {"resources": {"core": {"remaining": 0, "reset": 1}}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    assert mod.load_input() == payload


def test_load_input_invalid_json_exits_2(mod, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not-json"))
    with pytest.raises(SystemExit) as exc:
        mod.load_input()

    assert exc.value.code == mod.EXIT_NO_MATCH
    assert "Failed to parse JSON from stdin" in capsys.readouterr().err


def test_load_input_non_object_exits_2(mod, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("[]"))
    with pytest.raises(SystemExit) as exc:
        mod.load_input()

    assert exc.value.code == mod.EXIT_NO_MATCH
    assert "Input JSON must be an object" in capsys.readouterr().err


def test_load_payload_uses_gh_api_when_stdin_is_tty(mod, monkeypatch):
    class DummyTTY:
        def isatty(self):
            return True

    monkeypatch.setattr(sys, "stdin", DummyTTY())
    monkeypatch.setattr(
        mod,
        "load_from_gh_api",
        lambda: {"resources": {"core": {"remaining": 0, "reset": 1}}},
    )
    assert mod.load_payload() == {"resources": {"core": {"remaining": 0, "reset": 1}}}


def test_load_payload_uses_stdin_when_not_tty(mod, monkeypatch):
    expected = {"resources": {"search": {"remaining": 1, "reset": 2}}}
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    monkeypatch.setattr(mod, "load_input", lambda: expected)
    assert mod.load_payload() == expected


def test_resolve_timezone_invalid_exits_2(mod, capsys):
    with pytest.raises(SystemExit) as exc:
        mod.resolve_timezone("No/Such_TZ")

    assert exc.value.code == mod.EXIT_NO_MATCH
    assert "Invalid timezone: No/Such_TZ" in capsys.readouterr().err


def run_main(mod, monkeypatch, capsys, payload, *args):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(sys, "argv", ["gh-whenreset", *args])
    code = mod.main()
    captured = capsys.readouterr()
    return code, captured.out.strip(), captured.err.strip()


def test_main_default_uses_latest_exhausted_bucket(mod, monkeypatch, capsys):
    now = int(datetime.now(tz=ZoneInfo("UTC")).timestamp())
    payload = {
        "resources": {
            "core": {"remaining": 0, "reset": now + 300},
            "search": {"remaining": 1, "reset": now + 1000},
            "graphql": {"remaining": 0, "reset": now + 600},
        }
    }

    code, out, err = run_main(mod, monkeypatch, capsys, payload, "--tz", "UTC")
    assert code == 0
    assert err == ""

    parts = out.split("\t")
    assert len(parts) == 3
    timestamp, bucket, relative = parts
    assert bucket == "graphql"
    assert re.match(r"^(in \d+(s|min|h|d)|\d+(s|min|h|d) ago)$", relative)
    parsed = datetime.fromisoformat(timestamp)
    assert parsed.tzinfo is not None


def test_main_all_considers_all_buckets(mod, monkeypatch, capsys):
    now = int(datetime.now(tz=ZoneInfo("UTC")).timestamp())
    payload = {
        "resources": {
            "core": {"remaining": 0, "reset": now + 120},
            "search": {"remaining": 2, "reset": now + 900},
        }
    }

    code, out, err = run_main(mod, monkeypatch, capsys, payload, "--all", "--tz", "UTC")
    assert code == 0
    assert err == ""
    assert "\tsearch\t" in out


def test_main_no_exhausted_bucket_exits_2(mod, monkeypatch, capsys):
    payload = {
        "resources": {
            "core": {"remaining": 3, "reset": 1700000000},
            "search": {"remaining": 1, "reset": 1700000300},
        }
    }

    code, out, err = run_main(mod, monkeypatch, capsys, payload, "--tz", "UTC")
    assert code == mod.EXIT_NO_MATCH
    assert out == ""
    assert "No rate limit buckets matched" in err


def test_main_missing_resources_exits_2(mod, monkeypatch, capsys):
    code, out, err = run_main(mod, monkeypatch, capsys, {"rate": {}}, "--tz", "UTC")
    assert code == mod.EXIT_NO_MATCH
    assert out == ""
    assert "missing object field: resources" in err
