import asyncio
import random
from datetime import datetime

from loguru import logger
from simple_pid import PID

from src.config import Config
from src.demo_stand.demo_call import DemoCall
from src.demo_stand.demo_oper import DemoOper
from src.http_clients.db_buffer_client import DbBufferClient


class DemoSkillUnit(object):
    def __init__(self,
                 config: Config,
                 db_buffer_client: DbBufferClient,
                 sqlite_connection,
                 skill_id: int):
        self.config: Config = config
        self.db_buffer_client: DbBufferClient = db_buffer_client
        self.sqlite_connection = sqlite_connection
        self.skill_id: int = skill_id
        self.active: bool = True
        self.current_power: int = 0
        self.current_all: int = 0
        self.current_online: int = 0
        self.current_busy: int = 0
        self.current_wait: int = 0
        self.agr_sum_wait: int = 0
        self.pid_disabled: bool = False
        self.wanted_ratio: float = 0.99
        self.kp: float = 0.0
        self.ki: float = 0.0
        self.kd: float = 0.0
        self.update_time: int = 10
        self.start_time = datetime.now()
        self.last_time = datetime.now()
        self.active_demo_calls: dict[str, DemoCall] = {}
        self.active_demo_opers: dict[int, DemoOper] = {}
        self.sequence_lead_id: int = 1000

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

    async def run_calls(self) -> list[dict]:
        batch_size = int(self.current_power * self.update_time)
        for _ in range(batch_size):
            delay = round(random.uniform(0, self.update_time), 3)
            new_demo_call = DemoCall(config=self.config,
                                     skill_id=self.skill_id,
                                     lead_id=self.sequence_lead_id,
                                     call_id=f'X{self.sequence_lead_id}',
                                     ring_duration=14.3,
                                     ivr_duration=20.5,
                                     redirect_duration=25.5,
                                     answer_percent=21,
                                     redirect_percent=12)

        print(batch_size)
        return []

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
            skill_detail = {}
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
            await asyncio.sleep(self.update_time)
            if self.active is False or self.pid_disabled is True:
                self.pid.reset()
                self.current_power = 0
                await asyncio.sleep(1)
                continue

            current_stats = {
                "online": self.current_online,
                "busy": self.current_busy,
                "wait": self.current_wait,
                "count_call": len(self.active_demo_calls)
            }

            self.current_power = int(self.pid(self.current_busy + self.current_wait))

            self.log.info(f'current_stats={current_stats} power={self.current_power}')

            self.pid.setpoint = int(self.current_online * self.wanted_ratio)

            await self.run_calls()
