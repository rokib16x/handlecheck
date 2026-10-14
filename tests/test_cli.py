import json

from handlecheck import Status, cli
from handlecheck.checkers import Result


def fake_check_all(name, platforms=None):
    return [Result("youtube", name, Status.FOUND, f"https://www.youtube.com/@{name}")]


def test_json_output(monkeypatch, capsys):
    monkeypatch.setattr(cli, "check_all", fake_check_all)
    assert cli.main(["--delay", "0", "--format", "json", "a", "b"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [d["username"] for d in data] == ["a", "b"]
    assert data[0]["status"] == "FOUND"


def test_file_input_skips_comments(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(cli, "check_all", fake_check_all)
    f = tmp_path / "names.txt"
    f.write_text("# comment\none\n\ntwo\n")
    cli.main(["--delay", "0", "--format", "csv", "-f", str(f)])
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 3  # header + 2 rows


def test_no_args_prints_help(capsys):
    assert cli.main([]) == 2
    assert "usage" in capsys.readouterr().out.lower()
