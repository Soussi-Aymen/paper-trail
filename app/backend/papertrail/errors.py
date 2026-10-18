from fastapi.responses import JSONResponse


def problem(
    status: int,
    type_slug: str,
    title: str,
    detail: str,
    retry_after: str | None = None,
) -> JSONResponse:
    response = JSONResponse(
        status_code=status,
        media_type="application/problem+json",
        content={
            "type": f"urn:papertrail:{type_slug}",
            "title": title,
            "status": status,
            "detail": detail,
        },
    )
    if retry_after:
        response.headers["Retry-After"] = retry_after
    return response
