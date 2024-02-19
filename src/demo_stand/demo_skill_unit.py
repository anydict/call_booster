import asyncio
import random
import sqlite3
from asyncio import Future
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
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
                 skill_id: int,
                 kp: float,
                 ki: float,
                 kd: float,
                 update_time: int):
        self.config: Config = config
        self.db_buffer_client: DbBufferClient = db_buffer_client
        self.sqlite_connection = sqlite_connection
        self.skill_id: int = skill_id
        self.active: bool = True
        self.current_power: float = 0
        self.current_online: int = 50
        self.approximate_busy: float = 0
        self.current_busy: float = 0
        self.current_wait: int = 0
        self.agr_sum_wait: int = 0
        self.pid_disabled: bool = False
        self.wanted_ratio: float = 0.99
        self.kp: float = kp
        self.ki: float = ki
        self.kd: float = kd
        self.update_time: int = update_time
        self.start_time = datetime.now()
        self.last_time = datetime.now()
        self.active_demo_calls: dict[int, DemoCall] = {}
        self.active_demo_opers: dict[int, DemoOper] = {}
        self.sequence_call_id: int = 1000
        self.hotline_counter: int = 0
        self.occupy_counter: int = 0
        self.count_raw_call: int = 0
        self.history_current_busy = []

        self.pid = PID(Kp=self.kp, Ki=self.ki, Kd=self.kd, setpoint=self.current_online)
        self.log = logger.bind(object_id=f'{self.__class__.__name__}-{skill_id}')

    def generate_call_id(self):
        self.sequence_call_id += 1
        return self.sequence_call_id

    def new_row_skill_chart(self) -> None:
        """Add new row in skill_chart"""
        pass
        # try:
        #     cursor = self.sqlite_connection.cursor()
        #     cursor.execute(' INSERT INTO skill_chart '
        #                    ' (skill_id, calc_time, cnt_online, cnt_busy, '
        #                    '  cnt_wait_oper, power) '
        #                    ' VALUES (?, ?, ?, ?, ?, ?)',
        #                    (self.skill_id, datetime.now().isoformat(), self.current_online, self.current_busy,
        #                     self.current_wait, self.current_power))
        #     self.sqlite_connection.commit()
        # except Exception as e:
        #     self.log.warning(e)

    def switch_active(self, active: bool):
        if self.active != active:
            self.active = active
            self.log.info(f'new active = {active} for skill_id={self.skill_id}')

    async def run_demo_calls(self) -> None:
        if self.current_power <= 0:
            return

        self.count_raw_call += int(self.current_power * self.update_time)

        answer_percent = max(float(np.random.normal(loc=0.6, scale=0.05)), 0)
        redirect_percent = max(float(np.random.normal(loc=0.005, scale=0.002)), 0)
        batch_size = int(self.current_power * self.update_time * answer_percent * redirect_percent)

        if self.config.demo_log:
            self.log.info(f" batch_size={batch_size} current_power={self.current_power} update_time={self.update_time}"
                          f" answer_percent={answer_percent} redirect_percent={redirect_percent} "
                          f" count_raw_call={self.count_raw_call}")
        if batch_size <= 0:
            return

        for _ in range(batch_size):
            call_id = self.generate_call_id()
            delay = round(random.uniform(0, self.update_time), 3)
            ring_duration = max(float(np.random.normal(loc=16.5, scale=3)), 6)
            ivr_duration = max(float(np.random.normal(loc=31, scale=1)), 6)
            redirect_duration = float(np.random.normal(loc=80, scale=15) * np.random.normal(loc=1.2, scale=0.25))
            redirect_duration = max(redirect_duration, 2)

            date_call: datetime = datetime.now() + timedelta(seconds=delay)
            date_answer: datetime = date_call + timedelta(seconds=ring_duration)
            redirect_search: datetime = date_answer + timedelta(seconds=ivr_duration)
            redirect_call: datetime = redirect_search + timedelta(seconds=3)
            redirect_answer: datetime = redirect_call + timedelta(seconds=1)
            date_end: datetime = redirect_answer + timedelta(seconds=redirect_duration)

            if self.config.demo_log:
                self.log.info(f"new call: call_id={call_id} date_call={date_call} date_answer={date_answer} "
                              f"redirect_search={redirect_search} redirect_call={redirect_call} "
                              f"redirect_answer={redirect_answer} date_end={date_end}")

            new_demo_call = DemoCall(config=self.config,
                                     skill_id=self.skill_id,
                                     call_id=call_id,
                                     date_call=date_call,
                                     date_answer=date_answer,
                                     redirect_search=redirect_search,
                                     redirect_call=redirect_call,
                                     redirect_answer=redirect_answer,
                                     date_end=date_end)
            self.active_demo_calls[call_id] = new_demo_call

    async def background_refresh_pid_params(self):
        while self.config.wait_shutdown is False:
            await asyncio.sleep(5)

            self.history_current_busy.append(self.current_busy)
            # self.pid.tunings = (1, 0.3, 0.4)
            # self.pid.output_limits = (0, 200)
            # self.wanted_ratio: float = 0.99
            # self.update_time: int = 20

    async def occupy_oper(self, call_id: int, date_end: datetime) -> Optional[int]:
        for oper in self.active_demo_opers.values():
            if oper.call_id is None and (oper.rest_end is None or datetime.now() > oper.rest_end):
                oper.call_id = call_id
                oper.date_end = date_end
                oper.rest_end = date_end + timedelta(seconds=oper.rest_time)
                self.occupy_counter += 1
                return oper.oper_id

        return None

    async def background_occupy_and_release_oper(self):
        while self.config.wait_shutdown is False:
            await asyncio.sleep(0.1)
            calls_for_remove = []
            for demo_call in self.active_demo_calls.values():
                if datetime.now() > demo_call.date_end:
                    if self.config.demo_log:
                        self.log.info(f'Call with call_id={demo_call.call_id} ended')
                    calls_for_remove.append(demo_call.call_id)
                    if demo_call.oper_id in self.active_demo_opers:
                        self.active_demo_opers[demo_call.oper_id].call_id = None
                        self.active_demo_opers[demo_call.oper_id].date_end = None
                        if self.config.demo_log:
                            self.log.info(f"unlink call_id={demo_call.oper_id} from oper_id={demo_call.oper_id}")
                    continue
                elif demo_call.oper_id is None and datetime.now() > demo_call.redirect_call:
                    if self.config.demo_log:
                        self.log.info(f"For call with call_id={demo_call.call_id} not found free oper during this time")
                    calls_for_remove.append(demo_call.call_id)
                    self.current_wait += 1
                    continue
                elif demo_call.oper_id is None and datetime.now() > demo_call.redirect_search:
                    demo_call.oper_id = await self.occupy_oper(call_id=demo_call.call_id,
                                                               date_end=demo_call.date_end)
                    if self.config.demo_log and demo_call.oper_id:
                        self.log.info(f"occupy oper_id={demo_call.oper_id} with call_id={demo_call.call_id}")

            for call_id in calls_for_remove:
                self.active_demo_calls.pop(call_id)

            current_busy = 0
            approximate_busy = 0
            for oper in self.active_demo_opers.values():
                if oper.call_id:
                    current_busy += 1
                    approximate_busy += 1
                elif oper.rest_end is not None and oper.rest_end > datetime.now():
                    approximate_busy += (oper.rest_end - datetime.now()).total_seconds() / oper.rest_time
                    current_busy += 1

            self.approximate_busy = approximate_busy

            if current_busy != self.current_busy:
                self.current_busy = current_busy
                if self.config.demo_log:
                    self.log.info(f"online={self.current_online} busy={self.current_busy} wait={self.current_wait} "
                                  f"hotline_counter={self.hotline_counter} power={self.current_power} "
                                  f"approximate_busy={self.approximate_busy}")

    async def start_booster(self):
        """Booster for start_call"""
        for oper_id in range(1, self.current_online + 1):
            self.active_demo_opers[oper_id] = DemoOper(config=self.config,
                                                       skill_id=self.skill_id,
                                                       oper_id=oper_id,
                                                       rest_time=20)

        asyncio.create_task(self.background_refresh_pid_params())
        asyncio.create_task(self.background_occupy_and_release_oper())

        self.pid.output_limits = (0, 22200)

        while self.config.wait_shutdown is False:
            try:
                if self.active is False or self.pid_disabled is True:
                    self.pid.reset()
                    self.current_power = 0
                    await asyncio.sleep(1)
                    continue

                current_stats = {
                    "online": self.current_online,
                    "busy": self.current_busy,
                    "wait": self.current_wait,
                    "count_call": len(self.active_demo_calls),
                    "hotline_counter": self.hotline_counter,
                    "occupy_counter": self.occupy_counter,
                    "count_raw_call": self.count_raw_call
                }

                feedback = self.approximate_busy + self.current_wait

                self.current_power = round(self.pid(feedback), 3)
                self.hotline_counter += self.current_wait
                self.current_wait = 0  # reset wait counter
                self.pid.setpoint = int(self.current_online * self.wanted_ratio)

                self.new_row_skill_chart()

                if self.config.demo_log:
                    self.log.info(f" current_stats={current_stats} power={self.current_power} "
                                  f" feedback={feedback} setpoint={self.pid.setpoint}")

                if datetime.now() > self.start_time + timedelta(minutes=55):
                    with open("pid_params_stats.txt", 'a', encoding='utf-8') as txt_file:
                        avg_busy = round(sum(self.history_current_busy) / len(self.history_current_busy), 3)
                        # row = f"kp={self.kp} ki={self.ki} kd={self.kd} " \
                        #       f"update_time={self.update_time} count_raw_call={self.count_raw_call}\n"
                        row = f"{self.kp};{self.ki};{self.kd};{self.update_time};{self.count_raw_call};" \
                              f"{self.hotline_counter};{self.occupy_counter};{avg_busy}\n"
                        txt_file.write(row)
                        break

                await self.run_demo_calls()
            except Exception as e:
                self.log.exception(e)
            except KeyboardInterrupt:
                self.log.warning('KeyboardInterrupt')
            finally:
                await asyncio.sleep(self.update_time)


async def brute_force_pid_params():
    cfg: Config = Config()
    cfg.demo_log = False

    connection = sqlite3.connect('chart_database.db', check_same_thread=False)
    dbb_client: DbBufferClient = DbBufferClient(config=cfg)

    crs = connection.cursor()

    crs.execute('DROP TABLE skill_chart;')

    # Создаем таблицу Users
    crs.execute('''
    CREATE TABLE IF NOT EXISTS skill_chart (
    skill_id INTEGER NOT NULL,
    calc_time TEXT NOT NULL,
    cnt_online INTEGER NOT NULL,
    cnt_busy INTEGER NOT NULL,
    cnt_wait_oper INTEGER NOT NULL,
    power INTEGER
    )
    ''')
    connection.commit()

    tasks: list[Future] = []
    brute_force_kp = [4 + x * 0.1 for x in range(0, 20)]
    brute_force_ki = [0.001 + x * 0.01 for x in range(0, 9)]
    brute_force_kd = [0.001 + x * 0.01 for x in range(0, 9)]
    brute_update_time = [x for x in range(5, 59)]
    skill_id = 0

    brute_force_kp = [4 + x * 0.1 for x in range(0, 20)]
    brute_force_ki = [0]
    brute_force_kd = [0]

    for update_time in brute_update_time:
        for kp in brute_force_kp:
            for ki in brute_force_ki:
                for kd in brute_force_kd:
                    skill_id += 1

                    demo_skill_unit = DemoSkillUnit(config=cfg,
                                                    sqlite_connection=connection,
                                                    db_buffer_client=dbb_client,
                                                    skill_id=skill_id,
                                                    kp=kp,
                                                    ki=ki,
                                                    kd=kd,
                                                    update_time=update_time)
                    tasks.append(asyncio.create_task(demo_skill_unit.start_booster()))

    for task in tasks:
        await task
        logger.info(f'end task={task}')


if __name__ == '__main__':
    try:
        asyncio.run(brute_force_pid_params())
    except KeyboardInterrupt:
        logger.warning('KeyboardInterrupt')
