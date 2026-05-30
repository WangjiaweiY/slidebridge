from __future__ import annotations

import numpy as np
import pytest

from slidebridge.overlays.patches import load_patch_table


def test_load_patch_table_csv(tmp_path):
    path = tmp_path / "coords.csv"
    path.write_text("x,y,width,height,attention,label,index\n1,2,3,4,0.7,tumor,9\n", encoding="utf-8")

    table = load_patch_table(path)

    assert len(table) == 1
    assert table.records[0].score == 0.7
    assert table.records[0].label == "tumor"
    assert table.records[0].index == 9


def test_load_patch_table_npy_n2(tmp_path):
    path = tmp_path / "coords.npy"
    np.save(path, np.array([[1, 2], [3, 4]], dtype=np.float32))

    table = load_patch_table(path, default_patch_size=128)

    assert len(table) == 2
    assert table.records[0].width == 128


def test_load_patch_table_npy_n4(tmp_path):
    path = tmp_path / "coords.npy"
    np.save(path, np.array([[1, 2, 32, 64]], dtype=np.float32))

    table = load_patch_table(path)

    assert table.records[0].width == 32
    assert table.records[0].height == 64


def test_load_patch_table_npy_n5(tmp_path):
    path = tmp_path / "coords.npy"
    np.save(path, np.array([[1, 2, 32, 64, 0.9]], dtype=np.float32))

    table = load_patch_table(path)

    assert table.records[0].score == pytest.approx(0.9)


def test_load_patch_table_json_list(tmp_path):
    path = tmp_path / "coords.json"
    path.write_text('[{"x": 1, "y": 2, "width": 3, "height": 4, "score": 0.5}]', encoding="utf-8")

    table = load_patch_table(path)

    assert table.records[0].score == 0.5


def test_load_patch_table_json_object(tmp_path):
    path = tmp_path / "coords.json"
    path.write_text('{"patches": [{"x": 1, "y": 2}], "name": "demo"}', encoding="utf-8")

    table = load_patch_table(path, default_patch_size=77)

    assert table.records[0].width == 77
    assert table.metadata["name"] == "demo"


def test_load_patch_table_h5(tmp_path):
    h5py = pytest.importorskip("h5py")
    path = tmp_path / "coords.h5"
    with h5py.File(path, "w") as handle:
        handle.create_dataset("coords", data=np.array([[1, 2], [3, 4]], dtype=np.int64))
        handle.create_dataset("scores", data=np.array([0.1, 0.9], dtype=np.float32))
        handle.attrs["patch_size"] = 33

    table = load_patch_table(path)

    assert len(table) == 2
    assert table.records[0].width == 33
    assert table.records[1].score == pytest.approx(0.9)


def test_load_patch_table_pt_requires_torch_when_missing(tmp_path, monkeypatch):
    path = tmp_path / "coords.pt"
    path.write_bytes(b"not a real torch file")
    if pytest.importorskip("importlib").util.find_spec("torch") is not None:
        pytest.skip("torch is installed in this environment")

    with pytest.raises(RuntimeError, match="requires PyTorch"):
        load_patch_table(path)

