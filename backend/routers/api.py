"""API Router — all REST endpoints for the Architectural Multiverse Engine."""

import io
import zipfile
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel
from models.input_models import SystemInput, ScaffoldRequest
from models.architecture_models import ArchitectureResult, ComparisonResult, ScaffoldOutput
from services.architecture_generator import generate_architectures
from services.simulation_engine import simulate, compute_overall_score, get_scoring_breakdown
from services.comparison_service import compare
from services.scaffold_generator import generate_scaffold
from services.compliance_service import run_compliance_check
from services.srs_generator import generate_srs
from services.diagram_generator import generate_mermaid_diagram
from services.model_registry import get_all_models, set_model, MODULE_TYPES

router = APIRouter(prefix="/api", tags=["architecture"])


class CompareRequest(BaseModel):
    """Wraps architecture results with the original system input for comparison."""
    results: list[ArchitectureResult]
    system_input: SystemInput


class ModelConfigRequest(BaseModel):
    """Per-module model overrides."""
    strategic_analysis: str | None = None
    scaffold: str | None = None
    compliance: str | None = None
    trade_off: str | None = None
    srs: str | None = None
    diagram: str | None = None
    architecture: str | None = None
    scoring: str | None = None


class SRSRequest(BaseModel):
    """Request for SRS generation."""
    system_input: dict
    architecture_results: list[dict]
    comparison_result: dict


class DiagramRequest(BaseModel):
    """Request for diagram generation."""
    architecture: dict


# ═══════════════════════════════════════
#  Core Endpoints (existing)
# ═══════════════════════════════════════

@router.post("/generate", response_model=list[ArchitectureResult])
async def generate(inp: SystemInput):
    """Generate 4 architecture strategies with simulated scores."""
    architectures = generate_architectures(inp)
    results = []
    for arch in architectures:
        scores = simulate(arch, inp)
        overall = compute_overall_score(scores, inp)
        breakdown = get_scoring_breakdown(arch.name)
        results.append(ArchitectureResult(
            architecture=arch,
            scores=scores,
            overall_score=overall,
            scoring_breakdown=breakdown,
        ))
    return results


@router.post("/compare", response_model=ComparisonResult)
async def compare_architectures(req: CompareRequest):
    """Rank and compare architecture results with constraint & LLM analysis."""
    return compare(req.results, req.system_input)


@router.post("/scaffold", response_model=ScaffoldOutput)
async def scaffold(req: ScaffoldRequest):
    """Generate starter project scaffold for the chosen architecture."""
    files = generate_scaffold(req.architecture_name, req.system_description)
    return ScaffoldOutput(architecture_name=req.architecture_name, files=files)


# ═══════════════════════════════════════
#  Model Configuration
# ═══════════════════════════════════════

@router.get("/models")
async def get_models():
    """Get current model assignments for all modules."""
    return get_all_models()


@router.post("/models")
async def set_models(config: ModelConfigRequest):
    """Set model overrides per module."""
    overrides = config.model_dump(exclude_none=True)
    for module_type, model_name in overrides.items():
        if module_type in MODULE_TYPES:
            set_model(module_type, model_name)
    return get_all_models()


# ═══════════════════════════════════════
#  Compliance
# ═══════════════════════════════════════

@router.post("/compliance")
async def compliance_check(inp: SystemInput):
    """Analyze system description for regulatory compliance requirements."""
    system_dict = inp.model_dump() if hasattr(inp, "model_dump") else inp.dict()
    return run_compliance_check(system_dict)


# ═══════════════════════════════════════
#  Scaffold Download (ZIP)
# ═══════════════════════════════════════

@router.post("/scaffold/download")
async def scaffold_download(req: ScaffoldRequest):
    """Generate a scaffold and return it as a downloadable zip file."""
    files = generate_scaffold(req.architecture_name, req.system_description)

    # Build in-memory zip
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for filename, content in files.items():
            zf.writestr(filename, content)
    buffer.seek(0)

    slug = req.architecture_name.lower().replace(" ", "_").replace("-", "_")
    zip_filename = f"{slug}_scaffold.zip"

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"},
    )


# ═══════════════════════════════════════
#  SRS Generation
# ═══════════════════════════════════════

@router.post("/srs")
async def generate_srs_doc(req: SRSRequest):
    """Generate a Software Requirements Specification document."""
    srs_md = generate_srs(req.system_input, req.architecture_results, req.comparison_result)
    return PlainTextResponse(
        content=srs_md,
        media_type="text/markdown",
        headers={"Content-Disposition": "attachment; filename=srs_document.md"},
    )


# ═══════════════════════════════════════
#  Diagram Generation (Mermaid)
# ═══════════════════════════════════════

@router.post("/diagram")
async def generate_diagram(req: DiagramRequest):
    """Generate a Mermaid.js diagram for an architecture."""
    mermaid_code = generate_mermaid_diagram(req.architecture)
    return {"mermaid": mermaid_code}
