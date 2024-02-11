from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel
from starlette.responses import JSONResponse

from src.config import Config
from src.manager import Manager


class OriginateParams(BaseModel):
    token: str
    intphone: int
    extphone: int
    idclient: int
    dir: str
    calleridrule: str
    lead_id: int


class AnaliseParams(BaseModel):
    analise_name: str
    analise_time: str
    send_time: str
    token: str
    call_id: str
    info: dict


class HangupParams(BaseModel):
    token: str
    call_id: str


class Routers(object):
    def __init__(self, config, manager):
        self.config: Config = config
        self.manager: Manager = manager
        self.log = logger.bind(object_id=self.__class__.__name__)

        self.router = APIRouter(
            tags=["ALL"],
            responses={404: {"description": "Not found"}},
        )
        self.router.add_api_route(path="/", endpoint=self.get_root, methods=["GET"], tags=["Common"])
        self.router.add_api_route(path="/diag", endpoint=self.get_diag, methods=["GET"], tags=["Common"])
        self.router.add_api_route(path="/restart", endpoint=self.restart, methods=["POST"], tags=["Common"])

    def get_root(self):
        return JSONResponse(content={
            "app": self.config.app,
            "host": self.config.app_api_host,
            "port": self.config.app_api_port
        })

    def get_diag(self):
        return JSONResponse(content={
            "app": self.config.app,
            "wait_shutdown": self.config.wait_shutdown,
            "alive": self.config.alive,
        })

    def restart(self):
        self.config.wait_shutdown = True

        return JSONResponse(content={
            "app": self.config.app,
            "host": self.config.app_api_host,
            "port": self.config.app_api_port,
            "wait_shutdown": self.config.wait_shutdown,
            "alive": self.config.alive,
            "msg": "app restart started",
        })
