from datetime import datetime

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from loguru import logger
from starlette.responses import JSONResponse
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_404_NOT_FOUND


async def logging_dependency(request: Request):
    body_content = await request.body()
    body_content = body_content if len(body_content) < 1000 else f'len={len(body_content)}'

    logger.debug(f"{request.method} {request.url} body_content: {body_content} "
                 f"Params: {request.path_params.items()} "
                 f"Headers: {request.headers.items()}")


async def custom_request_validation_exception_handler(request: Request,
                                                      exc: RequestValidationError):
    """
    logging validation error

    @param request: API request
    @param exc: Error information
    """
    errors = ['ValidationError']
    for error in exc.errors():
        errors.append(f"loc: {error.get('loc')}; msg: {error.get('msg')}; type: {error.get('type')}")
    request_body = await request.body()
    request_body = request_body if len(str(request_body)) < 500 else f'len=({len(request_body)}'
    logger.error(f"ValidationError detail:"
                 f">>path: {request.url.path} "
                 f">>request_body: {request_body} "
                 f">>client_info: {request.client} "
                 f">>client_headers: {request.headers} "
                 f">>errors: {errors}")

    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "error", "msg": " ### ".join(errors)}
    )


async def custom_404_handler(request: Request, __):
    msg = f"{request.method} API handler for {request.url} not found"
    logger.warning(msg)
    response = {
        "status": "error",
        "msg": msg
    }
    return JSONResponse(content=response, status_code=HTTP_404_NOT_FOUND)


async def add_process_time_header(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds()
    if process_time > 1:
        logger.warning(f'Huge process time: {process_time}, {request.method} {request.url} {request.headers}')
    response.headers['X-Current-Time'] = datetime.now().isoformat()
    response.headers['X-Process-Time'] = str(process_time)
    response.headers['Cache-Control'] = 'no-cache, no-store'
    return response
