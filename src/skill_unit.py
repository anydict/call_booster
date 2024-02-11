import asyncio
import random
from datetime import datetime

from loguru import logger

from src.config import Config
from simple_pid import PID

from src.http_clients.call_direct_client import CallDirectClient
from src.http_clients.db_buffer_client import DbBufferClient
from src.http_clients.oper_dispatcher_client import OperDispatcherClient


class SkillUnit(object):
    def __init__(self,
                 config: Config,
                 oper_dispatcher_client: OperDispatcherClient,
                 db_buffer_client: DbBufferClient,
                 call_direct_clients: list[CallDirectClient],
                 skill_id: int):
        self.config: Config = config
        self.oper_dispatcher_client: OperDispatcherClient = oper_dispatcher_client
        self.db_buffer_client: DbBufferClient = db_buffer_client
        self.call_direct_clients: list[CallDirectClient] = call_direct_clients
        self.skill_id: int = skill_id
        self.active: bool = False
        self.current_all: int = 0
        self.current_online: int = 0
        self.current_busy: int = 0
        self.current_wait: int = 0
        self.current_power: int = 0
        self.update_time: int = 5
        self.start_time = datetime.now()
        self.last_time = datetime.now()
        self.log = logger.bind(object_id=f'{self.__class__.__name__}-{skill_id}')

    def update_detail(self,
                      new_all: int,
                      new_online: int,
                      new_busy: int,
                      new_wait: int,
                      new_power: int) -> int:
        self.log.info(f'new_all={new_all} new_online={new_online} new_busy={new_busy} '
                      f'new_wait={new_wait} new_power={new_power}')
        self.current_all = new_all
        self.current_online = new_online
        self.current_busy = new_busy
        self.current_wait = new_wait
        self.current_power = new_power

        return self.current_busy + self.current_wait

    def switch_active(self, active: bool):
        if self.active != active:
            self.active = active
            self.log.info(f'new active = {active} for skill_id={self.skill_id}')

    async def get_leads(self) -> list[dict]:
        if self.current_power <= 0:
            return []

        while self.config.wait_shutdown is False:
            leads = await self.db_buffer_client.get_leads(batch_size=self.current_power,
                                                          skill_id=self.skill_id)
            if leads:
                return leads
            else:
                self.log.debug(f'not found lead for skill_id={self.skill_id}')
                await asyncio.sleep(self.update_time)

    async def start_booster(self):
        """Booster for start_call"""
        pid = PID(5, 0.01, 0.1, setpoint=self.current_online)
        pid.output_limits = (0, 200)

        while self.config.wait_shutdown is False:
            if self.active:
                await asyncio.sleep(self.update_time)
            else:
                await asyncio.sleep(1)
                continue

            power = int(pid(self.current_busy + self.current_wait))

            skill_detail = await self.oper_dispatcher_client.get_skill_details(skill_id=self.skill_id)
            self.update_detail(new_all=skill_detail.get('all'),
                               new_online=skill_detail.get('online'),
                               new_busy=skill_detail.get('busy'),
                               new_wait=skill_detail.get('wait'),
                               new_power=power)

            pid.setpoint = self.current_online

            leads = await self.get_leads()
            if leads:
                for lead in leads:
                    delay = round(random.uniform(0, self.update_time), 3)
                    call_direct_client: CallDirectClient = random.choice(self.call_direct_clients)
                    asyncio.create_task(call_direct_client.start_call(lead=lead, delay=delay))
