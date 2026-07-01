"""
Local pipeline test — exercises the full Python analysis logic without Docker or GCP.

Layer 1: prepare_for_fastsurfer()       — NIfTI reorientation and compression
Layer 2: get_volume() / get_thickness() — FreeSurfer stats file parsing (batch pipeline)
Layer 3: compare_to_benchmark()         — full percentile computation against HCP-YA CSV
Layer 4: Full end-to-end API pipeline   — upload → LocalQueue → process_job (Docker mocked)
                                           → compare_to_benchmark → results endpoint
                                           All results asserted non-zero.

Five synthetic subjects are used.  NIfTI files come from nibabel's bundled anatomical.nii
(a real T1w brain, ~68 KB).  FreeSurfer stats files are hand-crafted fixtures that mirror
the exact format FastSurfer produces, letting the parsing and analysis code run for real.
"""

import io
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import nibabel as nib
import nibabel.orientations as nio
import numpy as np
import pytest
from fastapi.testclient import TestClient

# ── make backend importable ───────────────────────────────────────────────────
BACKEND = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(BACKEND))

# nibabel's built-in anatomical scan (real brain, ~68 KB uncompressed)
_NIB_ANAT = Path(nib.__file__).parent / "tests" / "data" / "anatomical.nii"

SUBJECTS = ["sub-001", "sub-002", "sub-003", "sub-004", "sub-005"]

# Subcortical volumes — chosen from aseg_mapping keys so extract_aseg_stats picks them up.
# Values are close to HCP-YA means so percentiles land around 0.50.
VOLUME_VALUES = {
    "Left-Caudate":          3816.0,
    "Right-Caudate":         3851.0,
    "Left-Putamen":          5571.0,
    "Right-Putamen":         5610.0,
    "Left-Accumbens-area":    540.0,
    "Right-Accumbens-area":   490.0,
    "Left-Cerebellum-Cortex":  62000.0,
    "Right-Cerebellum-Cortex": 63000.0,
}
ETIV = 1_500_000.0

# Cortical thickness — regions in preprocess.thickness_regions so extract_aparc_stats
# maps them to FS_L/R_*_Thck column names that exist in the HCP-YA CSV.
THICKNESS_VALUES = {
    "superiorfrontal":           2.45,
    "rostralmiddlefrontal":      2.30,
    "caudalmiddlefrontal":       2.20,
    "lateralorbitofrontal":      2.60,
    "medialorbitofrontal":       2.55,
    "rostralanteriorcingulate":  2.80,
    "caudalanteriorcingulate":   2.75,
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — synthetic FreeSurfer stats files
# ─────────────────────────────────────────────────────────────────────────────

def _aseg_stats(etiv: float, volumes: dict, scale: float = 1.0) -> str:
    lines = [
        "# Title Segmentation Statistics",
        "# generating_program mri_segstats",
        f"# Measure EstimatedTotalIntraCranialVol, eTIV,"
        f" Estimated Total Intracranial Volume, {etiv * scale:.1f}, mm^3",
    ]
    for i, (name, vol) in enumerate(volumes.items(), start=1):
        v = vol * scale
        lines.append(
            f"  {i:3d}   {i:3d}   {int(v):8d}   {v:10.1f}  {name}"
            "  0  0.0  0.0  0.0  0.0"
        )
    return "\n".join(lines) + "\n"


def _aparc_stats(thickness: dict, scale: float = 1.0) -> str:
    lines = [
        "# ColHeaders StructName NumVert SurfArea GrayVol"
        " ThickAvg ThickStd MeanCurv GausCurv FoldInd CurvInd",
    ]
    for name, thick in thickness.items():
        t = thick * scale
        lines.append(
            f"{name}   1000   800   2400   {t:.4f}"
            "   0.50   0.12   0.02   10   1.5"
        )
    return "\n".join(lines) + "\n"


def _populate_fastsurfer_output(base: Path, subject_id: str, scale: float = 1.0):
    """
    Write synthetic FreeSurfer stats into the directory tree FastSurfer produces.

    Created files:
      <base>/<subject_id>/stats/aseg.stats
      <base>/<subject_id>/stats/{lh,rh}.aparc.stats
      <base>/<subject_id>/stats/{lh,rh}.aparc.DKTatlas.mapped.stats   (get_thickness)
      <base>/<subject_id>/stats/{lh,rh}.aparc.DKTatlas.stats          (extract_aparc_stats)
    """
    stats_dir = base / subject_id / "stats"
    stats_dir.mkdir(parents=True, exist_ok=True)

    (stats_dir / "aseg.stats").write_text(_aseg_stats(ETIV, VOLUME_VALUES, scale=scale))
    aparc = _aparc_stats(THICKNESS_VALUES, scale=scale)
    for hemi in ("lh", "rh"):
        (stats_dir / f"{hemi}.aparc.stats").write_text(aparc)
        (stats_dir / f"{hemi}.aparc.DKTatlas.mapped.stats").write_text(aparc)
        (stats_dir / f"{hemi}.aparc.DKTatlas.stats").write_text(aparc)


# Place a real 1 mm isotropic T1w scan here to enable TestFullPipeline.
# Any .nii.gz brain scan works; FastSurfer requires proper resolution.
TEST_SCAN = Path(__file__).parent / "fixtures" / "test_scan.nii.gz"

requires_scan = pytest.mark.skipif(
    not TEST_SCAN.exists(),
    reason=f"No test scan found — place a T1w .nii.gz at {TEST_SCAN}",
)


def _real_brain_nii_gz() -> bytes:
    """Return the bytes of the test scan placed at tests/fixtures/test_scan.nii.gz."""
    return TEST_SCAN.read_bytes()


# ─────────────────────────────────────────────────────────────────────────────
# Session-scoped fixtures for the static dataset tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def tmp_root(tmp_path_factory):
    return tmp_path_factory.mktemp("mri_test")


@pytest.fixture(scope="session")
def nifti_input_dir(tmp_root):
    """
    Five subject directories with real T1w NIfTI scans covering every
    code path in prepare_for_fastsurfer():

    sub-001  RAS orientation, uncompressed .nii     → compress only
    sub-002  LAS orientation, uncompressed .nii     → reorient + compress
    sub-003  RAS orientation, uncompressed .nii     → compress only (same path as 001)
    sub-004  Pre-ready .nii.gz                      → skipped entirely
    sub-005  2 mm isotropic, uncompressed .nii      → voxel-size warning, then compress
    """
    input_dir = tmp_root / "nifti_input"
    base_img = nib.load(str(_NIB_ANAT))

    def _save(sid, img, gz=False):
        anat = input_dir / sid / "anat"
        anat.mkdir(parents=True, exist_ok=True)
        suffix = ".nii.gz" if gz else ".nii"
        nib.save(img, str(anat / f"{sid}_T1w{suffix}"))

    img_ras = nib.as_closest_canonical(base_img)
    _save("sub-001", img_ras)

    ornt_ras = nio.axcodes2ornt(nib.aff2axcodes(img_ras.affine))
    ornt_las = nio.axcodes2ornt(("L", "A", "S"))
    transform = nio.ornt_transform(ornt_ras, ornt_las)
    data_las = nio.apply_orientation(np.asarray(img_ras.dataobj), transform)
    new_aff = img_ras.affine.copy()
    new_aff[:3, 0] = -new_aff[:3, 0]
    _save("sub-002", nib.Nifti1Image(data_las, new_aff))

    _save("sub-003", img_ras)
    _save("sub-004", img_ras, gz=True)

    zooms = img_ras.header.get_zooms()
    hdr5 = img_ras.header.copy()
    hdr5.set_zooms((2.0, 2.0, 2.0) + zooms[3:])
    _save("sub-005", nib.Nifti1Image(np.asarray(img_ras.dataobj), img_ras.affine, hdr5))

    return input_dir


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "fastsurfer_output"


@pytest.fixture(scope="session")
def fastsurfer_output_dir():
    """
    Synthetic FastSurfer outputs for 5 subjects — written once to
    tests/fixtures/fastsurfer_output/ and reused across runs.
    """
    for i, sid in enumerate(SUBJECTS):
        _populate_fastsurfer_output(FIXTURES_DIR, sid, scale=1.0 + i * 0.02)
    return FIXTURES_DIR


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset module-level singletons and rate-limit counters between tests."""
    import storage
    import queue_system
    from app import limiter
    storage._backend = None
    queue_system._queue = None
    limiter._storage.reset()
    yield
    storage._backend = None
    queue_system._queue = None
    limiter._storage.reset()


# ─────────────────────────────────────────────────────────────────────────────
# Layer 1: NIfTI preprocessing
# ─────────────────────────────────────────────────────────────────────────────

class TestPreprocessing:
    def test_all_five_subjects_found(self, nifti_input_dir):
        from utils import prepare_for_fastsurfer
        assert set(prepare_for_fastsurfer(str(nifti_input_dir))) == set(SUBJECTS)

    def test_outputs_are_nii_gz(self, nifti_input_dir):
        from utils import prepare_for_fastsurfer
        prepare_for_fastsurfer(str(nifti_input_dir))
        for sid in SUBJECTS:
            assert (nifti_input_dir / sid / "anat" / f"{sid}_T1w.nii.gz").exists()

    def test_non_ras_reoriented_to_ras(self, nifti_input_dir):
        from utils import prepare_for_fastsurfer
        prepare_for_fastsurfer(str(nifti_input_dir))
        img = nib.load(str(nifti_input_dir / "sub-002" / "anat" / "sub-002_T1w.nii.gz"))
        assert nib.aff2axcodes(img.affine)[0] == "R"

    def test_uncompressed_becomes_gz(self, nifti_input_dir):
        from utils import prepare_for_fastsurfer
        prepare_for_fastsurfer(str(nifti_input_dir))
        gz = nifti_input_dir / "sub-003" / "anat" / "sub-003_T1w.nii.gz"
        assert gz.exists() and gz.stat().st_size > 0

    def test_pre_ready_subject_not_reprocessed(self, nifti_input_dir):
        from utils import prepare_for_fastsurfer
        gz = nifti_input_dir / "sub-004" / "anat" / "sub-004_T1w.nii.gz"
        mtime_before = gz.stat().st_mtime
        prepare_for_fastsurfer(str(nifti_input_dir))
        assert gz.stat().st_mtime == mtime_before


# ─────────────────────────────────────────────────────────────────────────────
# Layer 2: FreeSurfer stats parsing (batch pipeline path)
# ─────────────────────────────────────────────────────────────────────────────

class TestStatsParser:
    def test_get_volume_regions_and_etiv(self, fastsurfer_output_dir):
        from analysis import get_volume
        r = get_volume(str(fastsurfer_output_dir / "sub-001"), analysis="adhd")
        assert "error" not in r
        assert r["eTIV"] is not None
        assert abs(r["eTIV"] - ETIV) < 1.0
        for key in ("caudate_left", "caudate_right", "putamen_left", "putamen_right",
                    "accumbens_left", "accumbens_right",
                    "cerebellum_cortex_left", "cerebellum_cortex_right"):
            assert key in r["volumes"], f"Missing volume key: {key}"

    def test_get_volume_adjusted_keys_present(self, fastsurfer_output_dir):
        from analysis import get_volume
        r = get_volume(str(fastsurfer_output_dir / "sub-001"), analysis="adhd")
        assert "caudate_left_adjusted" in r["volumes"]

    def test_get_volume_values_correct(self, fastsurfer_output_dir):
        from analysis import get_volume
        r = get_volume(str(fastsurfer_output_dir / "sub-001"), analysis="adhd")
        assert abs(r["volumes"]["caudate_left"] - VOLUME_VALUES["Left-Caudate"]) < 1.0

    def test_get_thickness_14_keys(self, fastsurfer_output_dir):
        from analysis import get_thickness
        r = get_thickness(str(fastsurfer_output_dir / "sub-001"), analysis="adhd")
        assert "error" not in r
        assert len(r["thickness"]) == 14, f"Got {len(r['thickness'])} thickness keys"

    def test_get_thickness_values_correct(self, fastsurfer_output_dir):
        from analysis import get_thickness
        r = get_thickness(str(fastsurfer_output_dir / "sub-001"), analysis="adhd")
        assert abs(r["thickness"]["lh_dlpfc_superiorfrontal"] - THICKNESS_VALUES["superiorfrontal"]) < 0.001

    def test_missing_stats_returns_error_dict(self, tmp_path):
        from analysis import get_volume, get_thickness
        assert "error" in get_volume(str(tmp_path / "ghost"), analysis="adhd")
        assert "error" in get_thickness(str(tmp_path / "ghost"), analysis="adhd")

    def test_five_subjects_produce_distinct_volumes(self, fastsurfer_output_dir):
        from analysis import get_volume
        vals = [
            get_volume(str(fastsurfer_output_dir / sid), analysis="adhd")["volumes"]["caudate_left"]
            for sid in SUBJECTS
        ]
        assert len(set(round(v, 1) for v in vals)) == len(SUBJECTS)


# ─────────────────────────────────────────────────────────────────────────────
# Layer 3: compare_to_benchmark() — full Python path against the real HCP-YA CSV
# ─────────────────────────────────────────────────────────────────────────────

class TestBenchmarkComparison:
    def test_returns_both_categories(self, fastsurfer_output_dir):
        from analysis import compare_to_benchmark
        r = compare_to_benchmark(str(fastsurfer_output_dir / "sub-001"))
        assert "volume_percentiles" in r and "thickness_percentiles" in r

    def test_volume_percentiles_non_empty(self, fastsurfer_output_dir):
        from analysis import compare_to_benchmark
        r = compare_to_benchmark(str(fastsurfer_output_dir / "sub-001"))
        assert len(r["volume_percentiles"]) > 0

    def test_thickness_percentiles_non_empty(self, fastsurfer_output_dir):
        from analysis import compare_to_benchmark
        r = compare_to_benchmark(str(fastsurfer_output_dir / "sub-001"))
        assert len(r["thickness_percentiles"]) > 0

    def test_all_percentiles_nonzero_and_in_range(self, fastsurfer_output_dir):
        from analysis import compare_to_benchmark
        r = compare_to_benchmark(str(fastsurfer_output_dir / "sub-001"))
        for label, pct in r["volume_percentiles"] + r["thickness_percentiles"]:
            assert pct is not None, f"{label}: got None"
            assert 0.0 < pct < 1.0, f"{label}: percentile {pct} out of (0, 1)"

    def test_labels_are_human_readable(self, fastsurfer_output_dir):
        from analysis import compare_to_benchmark
        r = compare_to_benchmark(str(fastsurfer_output_dir / "sub-001"))
        for label, _ in r["volume_percentiles"]:
            assert not label.startswith("FS_"), f"Raw CSV column leaked: {label}"

    def test_all_five_subjects_succeed(self, fastsurfer_output_dir):
        from analysis import compare_to_benchmark
        for sid in SUBJECTS:
            r = compare_to_benchmark(str(fastsurfer_output_dir / sid))
            assert len(r["volume_percentiles"]) > 0, f"{sid}: empty volume_percentiles"
            assert len(r["thickness_percentiles"]) > 0, f"{sid}: empty thickness_percentiles"

    def test_larger_volume_yields_higher_percentile(self, fastsurfer_output_dir):
        """sub-005 has 8 % larger volumes than sub-001 → higher percentile on shared regions."""
        from analysis import compare_to_benchmark
        r1 = compare_to_benchmark(str(fastsurfer_output_dir / "sub-001"))
        r5 = compare_to_benchmark(str(fastsurfer_output_dir / "sub-005"))
        pct1 = {l: p for l, p in r1["volume_percentiles"] if p is not None}
        pct5 = {l: p for l, p in r5["volume_percentiles"] if p is not None}
        common = set(pct1) & set(pct5)
        assert common, "No overlapping volume labels"
        label = next(iter(common))
        assert pct5[label] > pct1[label]


# ─────────────────────────────────────────────────────────────────────────────
# Layer 4: Full end-to-end API pipeline — Docker mocked, everything else real
#
# The fake FastSurfer writes synthetic stats into the expected output path.
# The full chain runs: upload → LocalQueue → process_job → compare_to_benchmark
# (with real HCP-YA CSV) → results stored → /results endpoint returns them.
# All percentile results are asserted to be non-None and non-zero.
# ─────────────────────────────────────────────────────────────────────────────

PIPELINE_OUTPUT_DIR = Path(__file__).parent / "fixtures" / "web_jobs"
REPO_ROOT = Path(__file__).parent.parent


def _fake_fastsurfer(subjects, input_dir, output_dir, freesurfer_license, n_threads=4):
    """Write synthetic FastSurfer stats without running Docker."""
    for subject_id in subjects:
        _populate_fastsurfer_output(Path(output_dir), subject_id)


@pytest.fixture
def pipeline_client(tmp_path, monkeypatch):
    """
    Full-pipeline TestClient — Docker mocked with synthetic stats.

    The fake FastSurfer writes synthetic stats into the expected output path so
    the full chain (upload → LocalQueue → process_job → compare_to_benchmark →
    /results) runs without Docker or a FreeSurfer license.
    """
    monkeypatch.chdir(tmp_path)

    import storage, queue_system, utils
    storage._backend = None
    queue_system._queue = None

    PIPELINE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("worker.FASTSURFER_OUTPUT_DIR", str(PIPELINE_OUTPUT_DIR))
    monkeypatch.setattr(utils, "run_fastsurfer_docker", _fake_fastsurfer)

    from app import app
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client

    storage._backend = None
    queue_system._queue = None


@pytest.fixture
def docker_pipeline_client(tmp_path, monkeypatch):
    """
    Full-pipeline TestClient — FastSurfer runs for real via Docker.

    Requires Docker socket access and license.txt at the repo root (or
    FREESURFER_LICENSE env var).  Output persists in tests/fixtures/web_jobs/.
    """
    monkeypatch.chdir(tmp_path)

    import storage, queue_system, worker
    storage._backend = None
    queue_system._queue = None

    PIPELINE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(worker, "FASTSURFER_OUTPUT_DIR", str(PIPELINE_OUTPUT_DIR))
    monkeypatch.setattr(
        worker,
        "FREESURFER_LICENSE",
        str(REPO_ROOT / "license.txt"),
    )

    from app import app
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client

    storage._backend = None
    queue_system._queue = None


def _poll_until_done(client, job_id, timeout: float = 5400.0) -> str:
    """Return the final job status (completed/failed) or 'timeout'.
    Default timeout is 90 minutes to accommodate real FastSurfer runs."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = client.get(f"/status/{job_id}").json().get("status")
        if status in ("completed", "failed"):
            return status
        time.sleep(5.0)
    return "timeout"


@requires_scan
class TestDockerSmoke:
    """Verifies Docker connectivity by running the real pipeline for 30 s."""

    def test_job_runs_for_thirty_seconds(self, docker_pipeline_client):
        """Upload a scan and verify the job runs for 30 s without failing.

        A 'failed' status within 30 s means Docker is inaccessible or broken.
        'processing' after 30 s means Docker started successfully and is running.
        'completed' within 30 s is also accepted (unlikely with FastSurfer but valid).
        """
        resp = docker_pipeline_client.post(
            "/upload",
            files={"file": ("scan.nii.gz", _real_brain_nii_gz(), "application/gzip")},
        )
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        deadline = time.time() + 30
        while time.time() < deadline:
            status = docker_pipeline_client.get(f"/status/{job_id}").json().get("status")
            if status == "completed":
                return
            if status == "failed":
                error = docker_pipeline_client.get(f"/status/{job_id}").json().get("error", "")
                pytest.fail(f"Job failed within 30 s — Docker may not be accessible. Error: {error}")
            time.sleep(1.0)

        final = docker_pipeline_client.get(f"/status/{job_id}").json().get("status")
        assert final == "processing", f"Expected 'processing' after 30 s, got '{final}'"


@requires_scan
class TestFullPipeline:
    def test_job_completes_successfully(self, pipeline_client):
        """Upload → background worker runs → job reaches 'completed' status."""
        resp = pipeline_client.post(
            "/upload",
            files={"file": ("scan.nii.gz", _real_brain_nii_gz(), "application/gzip")},
        )
        assert resp.status_code == 200
        job_id = resp.json()["job_id"]

        status = _poll_until_done(pipeline_client, job_id)
        assert status == "completed", f"Job ended with status '{status}'"

    def test_results_are_non_empty(self, pipeline_client):
        """Results endpoint returns both volume and thickness percentile lists."""
        job_id = pipeline_client.post(
            "/upload",
            files={"file": ("scan.nii.gz", _real_brain_nii_gz(), "application/gzip")},
        ).json()["job_id"]

        assert _poll_until_done(pipeline_client, job_id) == "completed"

        r = pipeline_client.get(f"/results/{job_id}")
        assert r.status_code == 200
        results = r.json()
        assert len(results["volume_percentiles"]) > 0, "No volume percentiles in results"
        assert len(results["thickness_percentiles"]) > 0, "No thickness percentiles in results"

    def test_all_percentiles_nonzero(self, pipeline_client):
        """Every returned percentile must be a real number in (0, 1) — no None, no zero."""
        job_id = pipeline_client.post(
            "/upload",
            files={"file": ("scan.nii.gz", _real_brain_nii_gz(), "application/gzip")},
        ).json()["job_id"]

        assert _poll_until_done(pipeline_client, job_id) == "completed"

        results = pipeline_client.get(f"/results/{job_id}").json()
        all_pcts = results["volume_percentiles"] + results["thickness_percentiles"]
        for label, pct in all_pcts:
            assert pct is not None, f"{label}: got None"
            assert 0.0 < pct < 1.0, f"{label}: percentile {pct} out of (0, 1)"

    def test_volume_labels_human_readable(self, pipeline_client):
        """Volume labels must come from human_readable_cols, not raw CSV column names."""
        job_id = pipeline_client.post(
            "/upload",
            files={"file": ("scan.nii.gz", _real_brain_nii_gz(), "application/gzip")},
        ).json()["job_id"]

        assert _poll_until_done(pipeline_client, job_id) == "completed"

        results = pipeline_client.get(f"/results/{job_id}").json()
        for label, _ in results["volume_percentiles"]:
            assert not label.startswith("FS_"), f"Raw CSV column in output: {label}"

    def test_status_lifecycle(self, pipeline_client):
        """Job transitions through queued → processing/completed, never unknown states."""
        job_id = pipeline_client.post(
            "/upload",
            files={"file": ("scan.nii.gz", _real_brain_nii_gz(), "application/gzip")},
        ).json()["job_id"]

        seen = set()
        deadline = time.time() + 15
        while time.time() < deadline:
            status = pipeline_client.get(f"/status/{job_id}").json().get("status")
            seen.add(status)
            if status in ("completed", "failed"):
                break
            time.sleep(0.1)

        assert "completed" in seen, f"Never reached completed; saw: {seen}"
        unknown = seen - {"queued", "processing", "completed", "failed"}
        assert not unknown, f"Unexpected status values: {unknown}"

    def test_unknown_job_returns_404(self, pipeline_client):
        assert pipeline_client.get("/status/00000000-0000-0000-0000-000000000000").status_code == 404
        assert pipeline_client.get("/results/00000000-0000-0000-0000-000000000000").status_code == 404

    def test_multiple_jobs_get_distinct_ids_and_results(self, pipeline_client):
        """Two uploads must produce two distinct job IDs and two independent result sets."""
        ids = []
        for _ in range(2):
            r = pipeline_client.post(
                "/upload",
                files={"file": ("scan.nii.gz", _real_brain_nii_gz(), "application/gzip")},
            )
            assert r.status_code == 200
            ids.append(r.json()["job_id"])

        assert ids[0] != ids[1], "Duplicate job IDs"

        for job_id in ids:
            assert _poll_until_done(pipeline_client, job_id) == "completed"
            r = pipeline_client.get(f"/results/{job_id}")
            assert r.status_code == 200
            assert len(r.json()["volume_percentiles"]) > 0
