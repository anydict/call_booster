import asyncio
import os
import platform
import sys

import uvicorn
from fastapi import FastAPI, Depends
from fastapi.exceptions import RequestValidationError
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from src.api.api_utils import (custom_validation_exception_handler,
                               custom_404_handler,
                               add_process_time_header,
                               logging_dependency)
from src.api.routes import Routers
from src.config import Config, filter_error_log
from src.manager import Manager


async def app_startup():
    """Run our application"""
    app.manager = Manager(config=config)
    routers = Routers(config=config, manager=app.manager)

    app.include_router(routers.router, dependencies=[Depends(logging_dependency)])

    asyncio.create_task(app.manager.start_manager())


async def app_shutdown():
    if hasattr(app, 'manager') and isinstance(app.manager, Manager):
        await app.manager.close_session()


if __name__ == "__main__":
    try:
        config_path = os.path.join('config', 'config.json')
        config = Config(config_path=config_path)

        logger.configure(extra={"object_id": "None"})  # Default values if not bind extra variable
        logger.remove()  # this removes duplicates in the console if we use custom log format

        # for console
        if config.console_log:
            logger.add(sink=sys.stdout,
                       format=config.log_format,
                       colorize=True)
        # different files for different message types
        logger.add(sink="logs/error.log",
                   filter=filter_error_log,
                   rotation="500 MB",
                   compression='gz',
                   format=config.log_format)
        logger.add(sink=f"logs/{config.app}.log",
                   rotation="500 MB",
                   compression='gz',
                   retention=10,
                   format=config.log_format)

        logger = logger.bind(object_id=os.path.basename(__file__))

        exception_handlers = {
            RequestValidationError: custom_validation_exception_handler,
            404: custom_404_handler
        }

        app = FastAPI(exception_handlers=exception_handlers,
                      version=config.app_version)

        app.add_middleware(BaseHTTPMiddleware,  # noqa
                           dispatch=add_process_time_header)

        app.add_middleware(CORSMiddleware,  # noqa
                           allow_origins=[f"http://{config.app_api_host}:{config.app_api_port}"],
                           allow_credentials=True,
                           allow_methods=["*"],
                           allow_headers=["*"])

        logger.info("=" * 40, "System Information", "=" * 40)
        uname = platform.uname()
        logger.info(f"System: {uname.system}")
        logger.info(f"Node Name: {uname.node}")
        logger.info(f"Release: {uname.release}")
        logger.info(f"Machine: {uname.machine}")
        logger.info(f"Parent pid: {os.getppid()}")
        logger.info(f"Current pid: {os.getpid()}")
        logger.info(f"API bind address: http://{config.app_api_host}:{config.app_api_port}")
        logger.info(f"Docs Swagger API address: http://{config.app_api_host}:{config.app_api_port}/docs")
        logger.info(f"OperDispatcher API address: http://{config.oper_dispatcher_host}:{config.oper_dispatcher_port}")
        logger.info(f"DbBuffer API address: http://{config.db_buffer_host}:{config.db_buffer_port}")
        logger.success(f"mock_api_request: {config.mock_api_request}")
        logger.info(f"App Version: {config.app_version}")
        logger.info(f"Python Version: {config.python_version}")

        uvicorn_log_config = uvicorn.config.LOGGING_CONFIG
        del uvicorn_log_config["loggers"]

        # Start FastAPI and our application in app_startup
        app.add_event_handler('startup', app_startup)
        app.add_event_handler('shutdown', app_shutdown)
        uvicorn.run(app=f'__main__:app',
                    host=config.app_api_host,
                    port=config.app_api_port,
                    log_level="info",
                    log_config=uvicorn_log_config,
                    reload=False)

        logger.info(f"Shutting down")
    except KeyboardInterrupt:
        logger.debug(f"User aborted through keyboard")
    except Exception as e:
        logger.exception(e)
