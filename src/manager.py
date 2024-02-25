import asyncio
import os
import sqlite3

from loguru import logger

from src.config import Config
from src.http_clients.call_direct_client import CallDirectClient
from src.http_clients.db_buffer_client import DbBufferClient
from src.http_clients.oper_dispatcher_client import OperDispatcherClient
from src.skill_unit import SkillUnit


class Manager(object):
    """He runs and controls other tasks and functions"""

    def __init__(self, config: Config):
        self.config: Config = config
        self.oper_dispatcher_client: OperDispatcherClient = OperDispatcherClient(config=config)
        self.db_buffer_client: DbBufferClient = DbBufferClient(config=config)
        self.call_direct_clients: list[CallDirectClient] = []
        self.log = logger.bind(object_id=self.__class__.__name__)
        self.skill_units: dict[int, SkillUnit] = {}
        self.sqlite_connector = sqlite3.connect('chart_database.db', check_same_thread=False)

    def __del__(self):
        self.log.debug('object has died')

    async def close_session(self):
        if self.config.alive:
            self.log.info('start close_session')
            self.sqlite_connector.close()
            await self.oper_dispatcher_client.close_session()
            await self.db_buffer_client.close_session()
            for call_direct_client in self.call_direct_clients:
                await call_direct_client.close_session()

            self.config.wait_shutdown = True
            self.config.alive = True
            self.log.info('end close_session')
            await asyncio.sleep(1)

    @staticmethod
    async def smart_sleep(delay: int):
        for _ in range(0, delay):
            await asyncio.sleep(1)

    async def alive_report(self):
        """
        This is an asynchronous function that runs in the background
        And logs a message every 60 seconds while the `alive` flag is set to `True`.

        @return None
        """
        while self.config.alive:
            self.log.info(f"alive, skill_units: {list(self.skill_units.keys())}")
            await self.smart_sleep(60)

        self.log.info('end alive report')

    async def start_manager(self):
        """
        Main function

        @return None
        """
        self.log.info('start_manager')
        asyncio.create_task(self.alive_report())

        cursor = self.sqlite_connector.cursor()

        # cursor.execute('DROP TABLE skill_chart;')

        # Создаем таблицу Users
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS skill_chart (
        skill_id INTEGER NOT NULL,
        calc_time TEXT NOT NULL,
        cnt_online INTEGER NOT NULL,
        cnt_busy INTEGER NOT NULL,
        cnt_wait_oper INTEGER NOT NULL,
        power INTEGER
        )
        ''')
        self.sqlite_connector.commit()

        for call_direct_address in self.config.call_direct_addresses:
            self.call_direct_clients.append(CallDirectClient(config=self.config,
                                                             api_url=call_direct_address))

        try:
            while self.config.wait_shutdown is False:
                await self.smart_sleep(5 if self.skill_units else 1)

                active_skills: list[int] = await self.oper_dispatcher_client.get_active_skills()
                self.log.info(f"Active skills in OperDispatcher : {active_skills}")
                for skill_id in active_skills:
                    if skill_id not in self.skill_units.keys():
                        skill_unit = SkillUnit(config=self.config,
                                               oper_dispatcher_client=self.oper_dispatcher_client,
                                               db_buffer_client=self.db_buffer_client,
                                               call_direct_clients=self.call_direct_clients,
                                               sqlite_connector=self.sqlite_connector,
                                               skill_id=skill_id)
                        self.skill_units[skill_id] = skill_unit
                        skill_unit.switch_active(active=True)
                        asyncio.create_task(skill_unit.start_booster())

                for skill_id in self.skill_units:
                    if skill_id not in active_skills:
                        self.skill_units[skill_id].switch_active(active=False)
                    else:
                        self.skill_units[skill_id].switch_active(active=True)

        except asyncio.CancelledError:
            self.log.warning('asyncio.CancelledError')

        await self.close_session()

        self.log.info('start_manager is end, go kill application')

        # close FastAPI and our application
        self.config.alive = False
        current_pid = os.getpid()
        os.kill(current_pid, 9)
