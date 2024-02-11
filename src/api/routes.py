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

        self.router.add_api_route(path="/skill/chart/{skill_id}", endpoint=self.get_skill_chart,
                                  methods=["GET"], tags=["Chart"])

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

    def get_skill_chart(self, skill_id: int, batch_size: int = 100):
        batch_size = batch_size if batch_size < 9999 else 9999

        skill_chart = self.manager.select_skill_chart(skill_id, batch_size)

        labels = []
        dataset1 = []
        dataset2 = []
        dataset3 = []
        dataset4 = []
        for row in skill_chart:
            labels.append(row[0])
            dataset1.append(row[1])
            dataset2.append(row[2])
            dataset3.append(row[3])
            dataset4.append(row[4])

        return JSONResponse(content={
            "skill_id": skill_id,
            "batch_size": batch_size,
            "labels": labels,
            "dataset1": dataset1,
            "dataset2": dataset2,
            "dataset3": dataset3,
            "dataset4": dataset4
        })
