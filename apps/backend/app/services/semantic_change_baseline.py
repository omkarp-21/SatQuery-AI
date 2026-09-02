"""COMPOSED_SEMANTIC_CHANGE_BASELINE - an isolated, experimental baseline for
mandatory capability C (bi-temporal semantic change).

    T1/T2  -> ChangeFormer mask (via run_change_slice, keeps ALL geospatial safeguards)
           -> connected components -> changed regions
           -> crop each region from T2 ("after")
           -> RemoteCLIP semantic tagging over a fixed RS change vocabulary
           -> deterministic rule-based change description
           -> mask + regions + tags + assembled description + evidence + provenance

This is **NOT**:
  - a temporal VLM
  - a learned semantic-change model
  - validated semantic reasoning

It is a composed baseline whose purpose is to establish the interface for C and
surface failure cases. RemoteCLIP tags are similarity to *given phrases*, not
calibrated semantic labels. No confidence value is produced.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
from typing import Any, Literal

import numpy as np
import rasterio
from pydantic import BaseModel
from scipy import ndimage

from satquery_evidence import (
    EvidenceItem,
    Provenance,
    SemanticVerificationResult,
    VerificationResult,
    new_evidence_id,
    verify,
    verify_semantic,
)
from satquery_model_adapters import AdapterRequest, RemoteClipAdapter

from app.services.temporal_slice import run_change_slice

BASELINE_NAME = "COMPOSED_SEMANTIC_CHANGE_BASELINE"

_DEFAULT_VOCAB = [
    "new buildings", "building demolition", "new road or paved surface",
    "vegetation loss", "new vegetation", "new water body", "bare soil or clearing",
    "construction site", "no notable change",
]
_REPO_ROOT = Path(__file__).resolve().parents[4]
_RC_CKPT = _REPO_ROOT / "models/cache/remoteclip/RemoteCLIP-ViT-B-32.pt"
_MIN_REGION_PX = 64  # ignore specks

# EXP-007b / G6 Phase 7 - how the T2 crop is taken for RemoteCLIP tagging.
#   tight       : exact changed-region bbox (original behaviour)
#   expanded    : bbox padded by _CONTEXT_PAD_FRAC on every side for surrounding context
#   mask_aware  : expanded crop, but pixels OUTSIDE the changed mask are dimmed so the
#                 tagger still sees context while the changed area dominates
CropStrategy = Literal["tight", "expanded", "mask_aware"]
_CONTEXT_PAD_FRAC = 0.75          # pad each side by 75% of the bbox extent
_MASK_AWARE_DIM = 0.35           # multiply non-changed pixels by this in mask_aware mode
_LOW_MARGIN = 0.05              # rank-1 minus rank-2 similarity below this -> low_margin advisory


class ChangeRegion(BaseModel):
    region_id: int
    area_px: int
    area_ha: float | None = None
    bbox_pixel: tuple[int, int, int, int]  # rmin, cmin, rmax, cmax
    bbox_lonlat: tuple[float, float, float, float] | None = None
    top_tag: str | None = None
    tag_ranking: list[list[Any]] = []
    tag_margin: float | None = None   # rank-1 minus rank-2 similarity
    low_margin: bool = False          # tag_margin < _LOW_MARGIN (advisory, not a confidence)


class ComposedSemanticChangeResult(BaseModel):
    baseline_name: str = BASELINE_NAME
    ok: bool
    errors: list[str] = []
    failures: list[str] = []  # per-region / per-step non-fatal failure cases
    disclaimer: str = (
        "composed baseline for capability C - NOT a temporal VLM, NOT learned "
        "semantic change, NOT validated semantic reasoning"
    )
    mask_path: str | None = None
    changed_fraction: float | None = None
    changed_area_ha: float | None = None
    regions: list[ChangeRegion] = []
    description: str | None = None
    evidence: list[EvidenceItem] = []
    verification: VerificationResult | None = None
    semantic_verification: SemanticVerificationResult | None = None
    provenance: dict[str, Any] = {}


def run_composed_semantic_change(
    t1_path: str | Path,
    t2_path: str | Path,
    *,
    checkpoint_dir: str | Path,
    remoteclip_checkpoint: str | Path | None = None,
    vocabulary: list[str] | None = None,
    max_regions: int = 6,
    crop_strategy: CropStrategy = "tight",
    artifact_dir: str | Path | None = None,
) -> ComposedSemanticChangeResult:
    started = time.time()
    vocab = vocabulary or _DEFAULT_VOCAB
    failures: list[str] = []

    # --- 1. ChangeFormer mask (reuses geospatial validation + co-reg gate) ---
    change = run_change_slice(
        t1_path, t2_path, checkpoint_dir=checkpoint_dir, strict=True, artifact_dir=artifact_dir
    )
    if not change.ok or change.stats is None or not change.mask_path:
        return ComposedSemanticChangeResult(
            ok=False, errors=change.errors or ["change slice produced no mask"],
            provenance={"change_slice": change.provenance},
        )

    m1 = change.t1_meta
    with rasterio.open(change.mask_path) as ds:
        mask = ds.read(1) > 127

    # --- 2. connected components -> regions ---
    labelled, n = ndimage.label(mask)
    comps = []
    for lab in range(1, n + 1):
        ys, xs = np.where(labelled == lab)
        if ys.size < _MIN_REGION_PX:
            continue
        comps.append((int(ys.size), lab, int(ys.min()), int(xs.min()), int(ys.max()), int(xs.max())))
    comps.sort(reverse=True)  # largest first
    if not comps:
        failures.append("no changed region above the minimum size threshold")

    # --- 3/4. crop T2 per region + RemoteCLIP tagging ---
    rc = RemoteClipAdapter(checkpoint=str(remoteclip_checkpoint or _RC_CKPT))
    regions: list[ChangeRegion] = []
    region_evidence: list[EvidenceItem] = []
    px_area = (m1.res[0] * m1.res[1]) if (m1 and m1.is_projected) else None

    h_full, w_full = labelled.shape
    with rasterio.open(t2_path) as t2ds:
        for (area_px, _lab, rmin, cmin, rmax, cmax) in comps[:max_regions]:
            reg = ChangeRegion(
                region_id=len(regions) + 1, area_px=area_px,
                area_ha=(round(area_px * px_area / 10_000.0, 4) if px_area else None),
                bbox_pixel=(rmin, cmin, rmax, cmax),
            )
            if m1 and m1.crs_epsg:
                from pyproj import Transformer
                a, b, c, d, e, f = m1.transform
                xs = [a * cc + b * rr + c for cc in (cmin, cmax + 1) for rr in (rmin, rmax + 1)]
                ys = [d * cc + e * rr + f for cc in (cmin, cmax + 1) for rr in (rmin, rmax + 1)]
                tr = Transformer.from_crs(f"EPSG:{m1.crs_epsg}", "EPSG:4326", always_xy=True)
                lo0, la0 = tr.transform(min(xs), min(ys))
                lo1, la1 = tr.transform(max(xs), max(ys))
                reg.bbox_lonlat = (round(min(lo0, lo1), 6), round(min(la0, la1), 6),
                                   round(max(lo0, lo1), 6), round(max(la0, la1), 6))

            try:
                # window bounds depend on the crop strategy
                if crop_strategy == "tight":
                    wr0, wc0, wr1, wc1 = rmin, cmin, rmax, cmax
                else:  # expanded | mask_aware share the padded window
                    pr = max(4, int(round((rmax - rmin + 1) * _CONTEXT_PAD_FRAC)))
                    pc = max(4, int(round((cmax - cmin + 1) * _CONTEXT_PAD_FRAC)))
                    wr0, wc0 = max(0, rmin - pr), max(0, cmin - pc)
                    wr1, wc1 = min(h_full - 1, rmax + pr), min(w_full - 1, cmax + pc)
                win = rasterio.windows.Window(wc0, wr0, max(wc1 - wc0 + 1, 8), max(wr1 - wr0 + 1, 8))
                crop = t2ds.read(indexes=[1, 2, 3], window=win, boundless=True, fill_value=0)
                crop = np.transpose(crop, (1, 2, 0)).astype("uint8")
                if crop.shape[0] < 8 or crop.shape[1] < 8:
                    failures.append(f"region {reg.region_id}: crop too small to tag")
                    regions.append(reg)
                    continue
                if crop_strategy == "mask_aware":
                    # dim everything outside THIS changed component, keep context faintly visible
                    sub = labelled[wr0:wr0 + crop.shape[0], wc0:wc0 + crop.shape[1]]
                    keep = (sub == _lab)
                    if keep.shape == crop.shape[:2] and keep.any():
                        dimmed = (crop.astype("float32") * _MASK_AWARE_DIM).astype("uint8")
                        crop = np.where(keep[..., None], crop, dimmed)
                tmp = Path(tempfile.mkdtemp(prefix="satq_reg_")) / f"r{reg.region_id}.png"
                from PIL import Image
                Image.fromarray(crop).save(tmp)
                res = rc.run(AdapterRequest(query=";".join(vocab), images=[str(tmp)],
                                            context={"task": "zero-shot-classification"}))
                reg.top_tag = res.answer["top_label"]
                reg.tag_ranking = res.answer["ranking"][:3]
                if len(reg.tag_ranking) >= 2:
                    reg.tag_margin = round(
                        float(reg.tag_ranking[0][1]) - float(reg.tag_ranking[1][1]), 4
                    )
                    reg.low_margin = reg.tag_margin < _LOW_MARGIN
                region_evidence.append(EvidenceItem(
                    evidence_id=new_evidence_id("ev-region"),
                    source_model="remoteclip", task="zero-shot-classification",
                    modality="optical-single", source_artifact=str(tmp),
                    spatial_region=({"bbox_lonlat": list(reg.bbox_lonlat)} if reg.bbox_lonlat else
                                    {"bbox_pixel": list(reg.bbox_pixel)}),
                    claim_supported=f"changed region {reg.region_id} most resembles {reg.top_tag!r}",
                    evidence_type="ranking",
                    payload={"top_label": reg.top_tag, "ranking": reg.tag_ranking},
                    provenance=res.provenance,
                ))
                Path(tmp).unlink(missing_ok=True)
            except Exception as exc:  # noqa: BLE001 - per-region failure is logged, not fatal
                failures.append(f"region {reg.region_id}: tagging failed ({type(exc).__name__})")
            regions.append(reg)

    # --- 5. deterministic rule-based description ---
    st = change.stats
    parts = [f"Detected change over ~{st.changed_area_ha or 0:.2f} ha "
             f"({st.changed_fraction:.1%} of the scene) across {len(regions)} region(s)."]
    for reg in regions:
        loc = ""
        if reg.bbox_lonlat:
            cx = (reg.bbox_lonlat[0] + reg.bbox_lonlat[2]) / 2
            cy = (reg.bbox_lonlat[1] + reg.bbox_lonlat[3]) / 2
            loc = f" near ({cx:.4f}, {cy:.4f})"
        a = f"~{reg.area_ha:.2f} ha" if reg.area_ha is not None else f"{reg.area_px} px"
        tag = f"resembles '{reg.top_tag}'" if reg.top_tag else "not taggable"
        parts.append(f"Region {reg.region_id} ({a}{loc}): {tag}.")
    description = " ".join(parts)

    # --- 6. evidence + verification + provenance ---
    mask_ev = EvidenceItem(
        evidence_id=new_evidence_id("ev-change"),
        source_model="changeformer", task="change-detection", modality="optical-bitemporal",
        source_artifact=change.mask_path,
        temporal_context={"t1": str(t1_path), "t2": str(t2_path), "relation": "T1 before T2"},
        claim_supported=f"~{st.changed_fraction:.1%} of pixels changed between T1 and T2",
        evidence_type="change-mask",
        payload={"mask_path": change.mask_path, "changed_fraction": st.changed_fraction,
                 "changed_area_ha": st.changed_area_ha, "n_regions": len(regions)},
        provenance=change.provenance.get("adapter_provenance", {}),
    )
    all_ev = [mask_ev, *region_evidence]
    vr = verify({"changed_fraction": st.changed_fraction}, all_ev, {
        "input_paths": [str(t1_path), str(t2_path)],
        "inputs_exist": {str(t1_path): True, str(t2_path): True},
        "requested_modality": "optical-bitemporal",
        "model_modalities": ["optical-bitemporal"],
        "pair_co_registered": change.pair.co_registered if change.pair else None,
    })
    # EXP-005b - model-independent semantic-coherence checks over the assembled
    # description + evidence (claim<->number/label, region geometry, area sums).
    # Not a real-world correctness judgement; see verify_semantic() docstring.
    scene_px = int(m1.width * m1.height) if (m1 and m1.width and m1.height) else None
    sem_vr = verify_semantic(
        {"description": description, "regions": [r.model_dump() for r in regions],
         "changed_area_ha": st.changed_area_ha},
        all_ev,
        {"image_shape": ((m1.height, m1.width) if (m1 and m1.height and m1.width) else None),
         "scene_pixels": scene_px, "changed_area_ha": st.changed_area_ha},
    )

    prov = {
        "baseline": BASELINE_NAME,
        "crop_strategy": crop_strategy,
        "stages": ["run_change_slice", "connected_components", f"region_crop[{crop_strategy}]",
                   "remoteclip_tagging", "rule_assemble", "evidence", "verify", "verify_semantic"],
        "change_slice_provenance": change.provenance,
        "remoteclip": Provenance.from_adapter(
            (region_evidence[0].provenance if region_evidence else {"model": "remoteclip"}),
            task="zero-shot-classification").model_dump(),
        "vocabulary": vocab,
        "n_components_total": int(n),
        "n_regions_tagged": sum(1 for r in regions if r.top_tag),
        "orchestration_runtime_s": round(time.time() - started, 3),
        "note": "RemoteCLIP tags are similarity to given phrases, not calibrated labels; no confidence produced",
    }

    return ComposedSemanticChangeResult(
        ok=True, failures=failures,
        mask_path=change.mask_path,
        changed_fraction=st.changed_fraction, changed_area_ha=st.changed_area_ha,
        regions=regions, description=description,
        evidence=all_ev, verification=vr, semantic_verification=sem_vr, provenance=prov,
    )
