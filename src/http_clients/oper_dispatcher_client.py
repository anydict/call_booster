import asyncio
import random
from typing import Optional

from loguru import logger

from src.config import Config
from src.custom_dataclasses.api_request import ApiRequest
from src.custom_dataclasses.api_response import ApiResponse
from src.http_clients.base_client import BaseClient


class OperDispatcherClient(BaseClient):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.log = logger.bind(object_id=f'{self.__class__.__name__}#{self.api_url}')
        self.log.info(f"create new client_session: {self.client_session}")

    @property
    def api_url(self):
        return f'{self.config.oper_dispatcher_host}:{self.config.oper_dispatcher_port}'

    async def get_active_skills(self) -> list[int]:
        if self.config.mock_api_request:
            await asyncio.sleep(0.2)
            active_skills = [1]
            if random.randrange(0, 20) == 0:
                active_skills.pop(0)

            return active_skills

        api_request: ApiRequest = ApiRequest(url=f'{self.api_url}/active_skills',
                                             method='GET',
                                             request={})
        api_response: ApiResponse = await self.send(api_request)
        if api_response.success:
            return api_response.result.get('active')
        else:
            return []

    async def get_skill_details(self, skill_id: int) -> Optional[dict]:
        if self.config.mock_api_request:
            await asyncio.sleep(0.2)
            busy = random.randrange(0, 11)
            wait = 0
            if busy == 10:
                wait = random.randrange(0, 5)

            details = {
                "all": 100,
                "online": 10,
                "busy": busy,
                "wait": wait
            }

            return details

        api_request: ApiRequest = ApiRequest(url=f'{self.api_url}/skill_details/{skill_id}',
                                             method='GET',
                                             request={})
        api_response: ApiResponse = await self.send(api_request)

        if api_response.success:
            return api_response.result.get('details')
        else:
            return None
