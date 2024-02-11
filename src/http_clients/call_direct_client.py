import asyncio

from loguru import logger

from src.config import Config
from src.custom_dataclasses.api_request import ApiRequest
from src.custom_dataclasses.api_response import ApiResponse
from src.http_clients.base_client import BaseClient


class CallDirectClient(BaseClient):
    def __init__(self, config: Config, api_url: str):
        super().__init__()
        self.config = config
        self.api_url: str = api_url
        self.log = logger.bind(object_id=f'{self.__class__.__name__}#{self.api_url}')
        self.log.info(f"create new client_session: {self.client_session}")

    async def start_call(self,
                         lead: dict,
                         delay: float) -> bool:
        await asyncio.sleep(delay)

        if self.config.mock_api_request:
            await asyncio.sleep(0.2)
            self.log.info(f'delay={delay} lead={lead}')
            return True

        api_request = ApiRequest(url=f'{self.api_url}/call/start',
                                 method='POST',
                                 request=lead)

        api_response: ApiResponse = await self.send(api_request)

        return api_response.success
