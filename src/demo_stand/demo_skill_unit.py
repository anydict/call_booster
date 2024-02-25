import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
from loguru import logger
from simple_pid import PID

from src.config import Config
from src.demo_stand.demo_call import DemoCall
from src.demo_stand.demo_oper import DemoOper


class DemoSkillUnit(object):
    def __init__(self,
                 config: Config,
                 skill_id: int,
                 update_time: int,
                 oper_online: int,
                 wanted_ratio: float,
                 kp: float,
                 ki: float,
                 kd: float,
                 min_oper_power: float,
                 max_oper_power: float
                 ):
        self.config: Config = config
        self.skill_id: int = skill_id
        self.update_time: int = update_time
        self.current_online: int = oper_online
        self.wanted_ratio: float = wanted_ratio
        self.kp: float = kp
        self.ki: float = ki
        self.kd: float = kd
        self.min_oper_power: float = min_oper_power
        self.max_oper_power: float = max_oper_power

        self.active: bool = True
        self.pid_disabled: bool = False

        self.current_power: float = 0
        self.current_busy: float = 0
        self.approximate_busy: float = 0
        self.current_wait: int = 0
        self.agr_sum_wait: int = 0
        self.start_time = datetime.now()
        self.last_time = datetime.now()
        self.active_demo_calls: dict[int, DemoCall] = {}
        self.online_demo_opers: dict[int, DemoOper] = {}
        self.sequence_call_id: int = 1000
        self.hotline_counter: int = 0
        self.occupy_counter: int = 0
        self.call_counter: int = 0
        self.call_wait_oper: set = set()
        self.history_current_busy = []

        self.pid = PID(Kp=self.kp, Ki=self.ki, Kd=self.kd, setpoint=self.current_online)

        self.pid.output_limits = (self.min_oper_power * self.current_online, self.max_oper_power * self.current_online)
        self.pid.setpoint = round(self.current_online * self.wanted_ratio, 2)
        self.log = logger.bind(object_id=f'{self.__class__.__name__}-{skill_id}')

    def generate_call_id(self):
        self.sequence_call_id += 1
        return self.sequence_call_id

    def switch_active(self, active: bool):
        if self.active != active:
            self.active = active
            self.log.info(f'new active = {active} for skill_id={self.skill_id}')

    async def run_demo_calls(self) -> None:
        if self.current_power <= 0:
            return

        self.call_counter += int(self.current_power * self.update_time)

        answer_ratio = max(float(np.random.normal(loc=0.6, scale=0.05)), 0)
        redirect_ratio = max(float(np.random.normal(loc=0.005, scale=0.002)), 0)
        batch_size = int(self.current_power * self.update_time * answer_ratio * redirect_ratio)

        if self.config.demo_log:
            self.log.info(f" batch_size={batch_size} current_power={self.current_power} update_time={self.update_time}"
                          f" answer_ratio={answer_ratio} redirect_ratio={redirect_ratio} "
                          f" call_counter={self.call_counter}")
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

    async def background_update_skill_chart(self):
        while self.config.wait_shutdown is False:
            await asyncio.sleep(5)
            self.history_current_busy.append(self.current_busy)

    async def occupy_oper(self, call_id: int, date_end: datetime) -> Optional[int]:
        order_online_demo_opers = [oper for oper in sorted(self.online_demo_opers.values(), key=lambda x: x.rest_time)]

        for oper in order_online_demo_opers:
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
                    # call ended
                    if self.config.demo_log:
                        self.log.info(f'Call with call_id={demo_call.call_id} ended')
                    calls_for_remove.append(demo_call.call_id)
                    if demo_call.oper_id in self.online_demo_opers:
                        self.online_demo_opers[demo_call.oper_id].call_id = None
                        if self.config.demo_log:
                            self.log.info(f"release oper_id={demo_call.oper_id} call_id={demo_call.oper_id} ")
                elif demo_call.oper_id is None and datetime.now() > demo_call.redirect_call:
                    # transfer to hotline
                    if self.config.demo_log:
                        self.log.info(f"For call with call_id={demo_call.call_id} not found free oper during this time")
                    calls_for_remove.append(demo_call.call_id)
                    self.call_wait_oper.discard(demo_call.call_id)
                    self.hotline_counter += 1
                elif demo_call.oper_id is None and datetime.now() > demo_call.redirect_search:
                    # search free oper
                    demo_call.oper_id = await self.occupy_oper(call_id=demo_call.call_id,
                                                               date_end=demo_call.date_end)
                    if demo_call.oper_id:
                        self.call_wait_oper.discard(demo_call.call_id)
                        if self.config.demo_log:
                            self.log.info(f"occupy oper_id={demo_call.oper_id} with call_id={demo_call.call_id}")
                    else:
                        # This call is waiting for some oper to be released
                        self.call_wait_oper.add(demo_call.call_id)

            for call_id in calls_for_remove:
                self.active_demo_calls.pop(call_id)

            current_busy = 0
            approximate_busy = 0
            for oper in self.online_demo_opers.values():
                if oper.call_id in self.active_demo_calls:
                    call = self.active_demo_calls[oper.call_id]
                    dialog_second = (datetime.now() - call.redirect_call).total_seconds()
                    current_busy += 1
                    approximate_busy += 1 if dialog_second < 60 else 0.9
                elif datetime.now() < oper.rest_end:
                    current_busy += 1
                    approximate_busy += (oper.rest_end - datetime.now()).total_seconds() / oper.rest_time * 0.6

            self.current_busy = current_busy
            self.approximate_busy = approximate_busy
            self.current_wait = len(self.call_wait_oper)

    async def start_booster(self):
        """Booster for start_call"""

        if self.config.demo_log:
            self.log.info(f'Create oper for current_online={self.current_online}')

        for oper_id in range(1, self.current_online + 1):
            self.online_demo_opers[oper_id] = DemoOper(config=self.config,
                                                       skill_id=self.skill_id,
                                                       oper_id=oper_id,
                                                       rest_time=20)

        asyncio.create_task(self.background_update_skill_chart())
        asyncio.create_task(self.background_occupy_and_release_oper())

        last_hotline_counter = 0

        while self.config.wait_shutdown is False:
            try:
                if self.active is False or self.pid_disabled is True:
                    self.pid.reset()
                    self.current_power = 0
                    await asyncio.sleep(1)
                    continue

                diff_hotline_counter = self.hotline_counter - last_hotline_counter
                last_hotline_counter = self.hotline_counter

                feedback = round(self.approximate_busy + self.current_wait + diff_hotline_counter, 3)
                self.current_power = round(self.pid(feedback), 3)

                if self.config.demo_log:
                    current_stats = {
                        "online": self.current_online,
                        "approximate_busy": self.approximate_busy,
                        "busy": self.current_busy,
                        "wait": self.current_wait,
                        "count_call": len(self.active_demo_calls),
                        "hotline_counter": self.hotline_counter,
                        "occupy_counter": self.occupy_counter,
                        "call_counter": self.call_counter,
                        "power": self.current_power,
                        "feedback": feedback,
                    }
                    self.log.info(f"current_stats={current_stats}")

                if datetime.now() > self.start_time + timedelta(minutes=120):
                    with open("pid_params_stats.txt", 'a', encoding='utf-8') as txt_file:
                        avg_busy = round(sum(self.history_current_busy) / len(self.history_current_busy), 3)
                        row = f"{self.kp};{self.ki};{self.kd};{self.update_time};{self.call_counter};" \
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
