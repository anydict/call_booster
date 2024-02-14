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
                 sqlite_connection,
                 skill_id: int):
        self.config: Config = config
        self.oper_dispatcher_client: OperDispatcherClient = oper_dispatcher_client
        self.db_buffer_client: DbBufferClient = db_buffer_client
        self.call_direct_clients: list[CallDirectClient] = call_direct_clients
        self.sqlite_connection = sqlite_connection
        self.skill_id: int = skill_id
        self.active: bool = False
        self.current_all: int = 0
        self.current_online: int = 0
        self.current_busy: int = 0
        self.current_wait: int = 0
        self.current_power: int = 0
        self.wanted_ratio: float = 0.99
        self.kp: float = 0.0
        self.ki: float = 0.0
        self.kd: float = 0.0
        self.update_time: int = 5
        self.start_time = datetime.now()
        self.last_time = datetime.now()
        self.pid = PID(self.kp, self.ki, self.kd, setpoint=self.current_online)

        self.log = logger.bind(object_id=f'{self.__class__.__name__}-{skill_id}')

    def new_row_skill_chart(self) -> None:
        """Add new row in skill_chart"""
        try:
            cursor = self.sqlite_connection.cursor()
            cursor.execute(' INSERT INTO skill_chart '
                           ' (skill_id, calc_time, cnt_online, cnt_busy, '
                           '  cnt_wait_oper, power) '
                           ' VALUES (?, ?, ?, ?, ?, ?)',
                           (self.skill_id, datetime.now().isoformat(), self.current_online, self.current_busy,
                            self.current_wait, self.current_power))
            self.sqlite_connection.commit()
        except Exception as e:
            self.log.warning(e)

    def switch_active(self, active: bool):
        if self.active != active:
            self.active = active
            self.log.info(f'new active = {active} for skill_id={self.skill_id}')

    async def get_leads(self) -> list[dict]:
        if self.current_power <= 0:
            return []

        batch_size = int(self.current_power * self.update_time)

        while self.config.wait_shutdown is False:
            leads = await self.db_buffer_client.get_leads(batch_size=batch_size,
                                                          skill_id=self.skill_id)
            if leads:
                return leads
            else:
                self.log.debug(f'not found lead for skill_id={self.skill_id}')
                self.pid.reset()
                self.current_power = 0
                await asyncio.sleep(self.update_time)

    async def background_refresh_pid_params(self):
        while self.config.wait_shutdown is False:
            await asyncio.sleep(5)
            # await new_pid_params = http_get_request(blabla)
            self.pid.tunings = (1, 0.01, 0.01)
            self.pid.output_limits = (0, 200)
            self.wanted_ratio: float = 0.99
            self.update_time: int = 5

    async def background_refresh_oper_stats(self):
        while self.config.wait_shutdown is False:
            await asyncio.sleep(5)
            skill_detail = await self.oper_dispatcher_client.get_skill_details(skill_id=self.skill_id)
            self.current_all = skill_detail.get('all', 0)
            self.current_online = skill_detail.get('online', 0)
            self.current_busy = skill_detail.get('busy', 0)
            self.current_wait = skill_detail.get('wait', 0)
            self.log.info(f'skill_detail={skill_detail} power={self.current_power}')
            self.new_row_skill_chart()

    async def start_booster(self):
        """Booster for start_call"""

        asyncio.create_task(self.background_refresh_pid_params())
        asyncio.create_task(self.background_refresh_oper_stats())

        self.pid.output_limits = (0, 200)

        while self.config.wait_shutdown is False:
            if self.active:
                await asyncio.sleep(self.update_time)
                self.pid.reset()
                self.current_power = 0
            else:
                await asyncio.sleep(1)
                continue

            skill_detail = await self.oper_dispatcher_client.get_skill_details(skill_id=self.skill_id)

            self.current_power = int(self.pid(self.current_busy + self.current_wait))

            self.current_all = skill_detail.get('all', 0)
            self.current_online = skill_detail.get('online', 0)
            self.current_busy = skill_detail.get('busy', 0)
            self.current_wait = skill_detail.get('wait', 0)

            self.log.info(f'skill_detail={skill_detail} power={self.current_power}')
            self.new_row_skill_chart()

            self.pid.setpoint = int(self.current_online * self.wanted_ratio)

            leads = await self.get_leads()
            if leads:
                for lead in leads:
                    delay = round(random.uniform(0, self.update_time), 3)
                    call_direct_client: CallDirectClient = random.choice(self.call_direct_clients)
                    asyncio.create_task(call_direct_client.start_call(lead=lead, delay=delay))
            else:
                self.log.warning(f'leads={leads}')
