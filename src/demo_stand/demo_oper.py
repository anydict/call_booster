from typing import Optional

from loguru import logger

from src.config import Config


class DemoOper(object):
    def __init__(self,
                 config: Config,
                 skill_id: int,
                 oper_id: int,
                 rest_time: int = 20,
                 ):
        self.config: Config = config
        self.skill_id: int = skill_id
        self.oper_id: int = oper_id
        self.rest_time: int = rest_time
        self.call_id: Optional[str] = None
        self.lead_id: Optional[int] = None

        self.log = logger.bind(object_id=f'{self.__class__.__name__}-{oper_id}')
