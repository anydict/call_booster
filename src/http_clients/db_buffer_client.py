import asyncio

from loguru import logger

from src.config import Config
from src.custom_dataclasses.api_request import ApiRequest
from src.custom_dataclasses.api_response import ApiResponse
from src.http_clients.base_client import BaseClient


class DbBufferClient(BaseClient):
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.log = logger.bind(object_id=f'{self.__class__.__name__}#{self.api_url}')
        self.log.info(f"create new client_session: {self.client_session}")

    @property
    def api_url(self):
        return f'{self.config.db_buffer_host}:{self.config.db_buffer_port}'

    async def get_leads(self, batch_size: int, skill_id: int) -> list[dict]:
        if self.config.mock_api_request:
            await asyncio.sleep(0.2)
            leads = []
            for lead_id in range(0, batch_size):
                leads.append({
                    "lead_id": lead_id,
                    "skill_id": skill_id,
                    "phone": f'phone_{lead_id}'
                })
            return leads

        api_request = ApiRequest(url=f'{self.api_url}/data/lead/{batch_size}',
                                 method='GET',
                                 request={})

        api_response: ApiResponse = await self.send(api_request)

        if api_response.success:
            return api_response.result.get('leads')
        else:
            return []
