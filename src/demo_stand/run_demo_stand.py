import asyncio
import sys

from loguru import logger

from src.config import Config
from src.demo_stand.demo_skill_unit import DemoSkillUnit


async def start_demo_stand():
    cfg: Config = Config()
    cfg.demo_log = True
    logger.configure(extra={"object_id": "None"})  # Default values if not bind extra variable
    logger.remove()  # this removes duplicates in the console if we use custom log format

    logger.add(sink=sys.stdout,
               format=cfg.log_format,
               colorize=True)
    logger.info(f"Подробные логи {'включены' if cfg.demo_log else 'ОТКЛЮЧЕНЫ'}")
    await asyncio.sleep(0.2)

    demo_skill_unit = DemoSkillUnit(config=cfg,
                                    skill_id=123456,
                                    update_time=10,
                                    oper_online=20,
                                    wanted_ratio=0.91,
                                    kp=4,
                                    ki=1,
                                    kd=1,
                                    min_oper_power=0.0,
                                    max_oper_power=10)

    await demo_skill_unit.start_booster()


if __name__ == '__main__':
    try:
        asyncio.run(start_demo_stand())
    except KeyboardInterrupt:
        logger.warning('KeyboardInterrupt')
