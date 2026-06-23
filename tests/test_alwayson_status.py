"""录制状态文件原子读写测试，供 /api/status 读。

不依赖硬件：纯文件读写。覆盖原子写、诚实回退（文件缺失/损坏不抛错）。
"""

from __future__ import annotations

from rapport.alwayson.status import read_status, write_status


def test_写后读回状态(tmp_path) -> None:
    p = tmp_path / "recording_status.json"
    write_status(p, recording=True, paused=False)
    assert read_status(p) == {"recording": True, "paused": False}


def test_文件不存在诚实回未录音(tmp_path) -> None:
    p = tmp_path / "nope.json"
    assert read_status(p) == {"recording": False, "paused": False}


def test_文件损坏诚实回未录音不抛错(tmp_path) -> None:
    p = tmp_path / "broken.json"
    p.write_text("{ not json", encoding="utf-8")
    assert read_status(p) == {"recording": False, "paused": False}


def test_缺字段时补全默认(tmp_path) -> None:
    p = tmp_path / "partial.json"
    p.write_text('{"recording": true}', encoding="utf-8")
    assert read_status(p) == {"recording": True, "paused": False}


def test_原子写不留临时文件(tmp_path) -> None:
    p = tmp_path / "recording_status.json"
    write_status(p, recording=True, paused=True)
    write_status(p, recording=False, paused=False)
    # 目录里只应有正式文件，没有遗留的 .tmp
    leftovers = [f.name for f in tmp_path.iterdir() if f.name != "recording_status.json"]
    assert leftovers == []
    assert read_status(p) == {"recording": False, "paused": False}


def test_clear_删除状态文件(tmp_path) -> None:
    from rapport.alwayson.status import clear_status

    p = tmp_path / "recording_status.json"
    write_status(p, recording=True, paused=False)
    clear_status(p)
    assert not p.exists()
    # 清掉后读回诚实未录音
    assert read_status(p) == {"recording": False, "paused": False}
    # 再清一次不抛错（幂等）
    clear_status(p)
