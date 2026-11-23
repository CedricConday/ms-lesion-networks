import numpy as np
import pytest

from lesionnet.overlap import tract_overlap


def grid():
    return np.zeros((10, 10, 10), dtype=np.float32)


def test_lesion_inside_binary_tract_gives_its_share():
    tract = grid()
    tract[2:8, 2:4, 2:4] = 1.0          # 24 voxels
    other = grid()
    other[0:2, 8:10, 8:10] = 1.0
    lesion = np.zeros(tract.shape, bool)
    lesion[3:6, 2:4, 2:4] = True        # 12 voxels, all inside the tract
    out = tract_overlap(lesion, {"A": tract, "B": other}, vox_ml=0.001).set_index("tract")
    assert out.loc["A", "tract_fraction"] == pytest.approx(12 / 24)
    assert out.loc["A", "lesion_ml"] == pytest.approx(12 * 0.001)
    assert out.loc["B", "tract_fraction"] == 0.0
    assert out.loc["B", "lesion_ml"] == 0.0


def test_probability_weighting():
    tract = grid()
    tract[0:5, 0, 0] = 0.5
    tract[5:10, 0, 0] = 1.0             # probability mass 7.5
    lesion = np.zeros(tract.shape, bool)
    lesion[4:6, 0, 0] = True            # one voxel at 0.5, one at 1.0 -> 1.5
    out = tract_overlap(lesion, {"A": tract}, vox_ml=1.0).iloc[0]
    assert out["lesion_ml"] == pytest.approx(1.5)
    assert out["tract_fraction"] == pytest.approx(1.5 / 7.5)


def test_lesion_outside_every_tract_is_zero_and_empty_tract_is_safe():
    tract = grid()
    tract[0, 0, 0] = 1.0
    lesion = np.zeros(tract.shape, bool)
    lesion[9, 9, 9] = True
    out = tract_overlap(lesion, {"A": tract, "empty": grid()}, vox_ml=1.0).set_index("tract")
    assert out["lesion_ml"].sum() == 0.0
    assert out.loc["empty", "tract_fraction"] == 0.0


def test_grid_mismatch_is_refused():
    with pytest.raises(ValueError):
        tract_overlap(np.zeros((4, 4, 4), bool), {"A": grid()}, vox_ml=1.0)
