import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.imports.detection import DETECT_SAMPLE_ROWS, detect_format_and_mapping
from app.imports.schema import DetectResponse, ValidateRequest, ValidateResponse
from app.imports.storage import get_upload_path, save_upload
from app.imports.validation import VALIDATE_SAMPLE_ROWS, apply_mapping, validate_mapping

router = APIRouter(prefix="/api/import", tags=["import"])


def _preview_records(df: pd.DataFrame, n: int = 10) -> list[dict]:
    head = df.head(n)
    return head.astype(object).where(pd.notna(head), None).to_dict(orient="records")


@router.post("/detect", response_model=DetectResponse)
async def detect(file: UploadFile = File(...)):
    content = await file.read()
    upload_id = save_upload(file.filename or "upload.csv", content)

    path = get_upload_path(upload_id)
    df = pd.read_csv(path, nrows=DETECT_SAMPLE_ROWS)

    detection = detect_format_and_mapping(df)

    return DetectResponse(
        upload_id=upload_id,
        format=detection["format"],
        column_mapping=detection["column_mapping"],
        wide_melt_preview=detection["wide_melt_preview"],
        preview_rows=_preview_records(df),
        row_count_sampled=len(df),
    )


@router.post("/validate", response_model=ValidateResponse)
def validate(request: ValidateRequest):
    try:
        path = get_upload_path(request.upload_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown upload_id")

    df = pd.read_csv(path, nrows=VALIDATE_SAMPLE_ROWS)
    result = validate_mapping(df, request.column_mapping, request.format)

    mapped_preview = apply_mapping(df, request.column_mapping, request.format)
    result["preview_rows"] = _preview_records(mapped_preview)

    return ValidateResponse(**result)
