from datetime import datetime
from typing import Optional

from loguru import logger

from src.config import Config


class DemoCall(object):
    def __init__(self,
                 config: Config,
                 skill_id: int,
                 lead_id: int,
                 call_id: str,
                 ring_duration: float,
                 ivr_duration: float,
                 redirect_duration: float,
                 answer_percent: float,
                 redirect_percent: float
                 ):
        self.config: Config = config
        self.skill_id: int = skill_id
        self.lead_id: int = lead_id
        self.call_id: str = call_id
        self.ring_duration: float = ring_duration
        self.ivr_duration: float = ivr_duration
        self.redirect_duration: float = redirect_duration
        self.answer_percent: float = answer_percent
        self.redirect_percent: float = redirect_percent
        self.date_call: datetime = datetime.now()
        self.date_answer: Optional[datetime] = None
        self.date_end: Optional[datetime] = None
        self.oper_id: Optional[int] = None
        self.redirect_call: Optional[datetime] = None
        self.redirect_answer: Optional[datetime] = None
        self.log = logger.bind(object_id=f'{self.__class__.__name__}-{lead_id}')
