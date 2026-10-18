from fastapi.responses import JSONResponse


def problem(status: int, type_slug: str, title: str, detail: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"urn:papertrail:{type_slug}",
            "title": title,
            "status": status,
            "detail": detail,
        },
    )
