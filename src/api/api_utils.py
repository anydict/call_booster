from datetime import datetime

from fastapi.exceptions import RequestValidationError
from loguru import logger
from fastapi import Request
from starlette import status
from starlette.responses import JSONResponse


async def logging_dependency(request: Request):
    body_content = await request.body()
    body_content = body_content if len(body_content) < 1000 else f'len={len(body_content)}'
    
    logger.debug(f"{request.method} {request.url} body: {body_content} "
                 f"Params: {request.path_params.items()} "
                 f"Headers: {request.headers.items()}")


async def custom_validation_exception_handler(request: Request,
                                              exc: RequestValidationError):
    """
    logging validation error

    @param request: API request
    @param exc: Error information
    """
    errors = ['ValidationError']
    for error in exc.errors():
        errors.append({
            'loc': error['loc'],
            'msg': error['msg'],
            'type': error['type']
        })
    logger.error(f"ValidationError in path: {request.url.path} request_body: {await request.body()}")
    logger.error(f"ValidationError detail: {errors}")
    logger.error(f"ValidationError client_info: {request.client}")
    logger.error(request.headers)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "error", "msg": " ### ".join(errors)}
    )


async def custom_404_handler(request: Request, __):
    msg = f"{request.method} API handler for {request.url} not found"
    logger.warning(msg)
    response = {
        "status": "error",
        "msg": msg
    }
    return JSONResponse(content=response, status_code=404)


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
