import asyncio
import sys
from asyncio import Future

from loguru import logger

from src.config import Config
from src.demo_stand.demo_skill_unit import DemoSkillUnit


async def brute_force_pid_params():
    cfg: Config = Config()
    cfg.demo_log = False
    logger.configure(extra={"object_id": "None"})  # Default values if not bind extra variable
    logger.remove()  # this removes duplicates in the console if we use custom log format

    logger.add(sink=sys.stdout,
               format=cfg.log_format,
               colorize=True)
    logger.info(f"Подробные логи {'включены' if cfg.demo_log else 'ОТКЛЮЧЕНЫ'}")
    await asyncio.sleep(0.2)

    tasks: list[Future] = []
    brute_force_kp = [2.2 + x * 0.1 for x in range(0, 10)]
    brute_force_ki = [0.002]
    brute_force_kd = [0]
    brute_update_time = [15, 21, 43, 60]
    skill_id = 1000

    for update_time in brute_update_time:
        for kp in brute_force_kp:
            for ki in brute_force_ki:
                for kd in brute_force_kd:
                    skill_id += 1
                    demo_skill_unit = DemoSkillUnit(config=cfg,
                                                    skill_id=skill_id,
                                                    update_time=update_time,
                                                    oper_online=20,
                                                    wanted_ratio=0.85,
                                                    kp=kp,
                                                    ki=ki,
                                                    kd=kd,
                                                    min_oper_power=0.0,
                                                    max_oper_power=1000.0)
                    tasks.append(asyncio.create_task(demo_skill_unit.start_booster()))

    for task in tasks:
        await task

    logger.info(f'All task ended')


if __name__ == '__main__':
    try:
        asyncio.run(brute_force_pid_params())
    except KeyboardInterrupt:
        logger.warning('KeyboardInterrupt')
