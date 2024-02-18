from datetime import datetime
from typing import Optional

from loguru import logger

from src.config import Config


class DemoCall(object):
    def __init__(self,
                 config: Config,
                 skill_id: int,
                 call_id: int,
                 date_call: datetime,
                 date_answer: datetime,
                 redirect_search: datetime,
                 redirect_call: datetime,
                 redirect_answer: datetime,
                 date_end: datetime):
        self.config: Config = config
        self.skill_id: int = skill_id
        self.call_id: int = call_id

        self.date_call: datetime = date_call
        self.date_answer: datetime = date_answer
        self.redirect_search: datetime = redirect_search
        self.redirect_call: datetime = redirect_call
        self.redirect_answer: datetime = redirect_answer
        self.date_end: datetime = date_end

        self.oper_id: Optional[int] = None
        self.log = logger.bind(object_id=f'{self.__class__.__name__}-{call_id}')
