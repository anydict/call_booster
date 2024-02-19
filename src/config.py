import json
import os
import platform
from datetime import datetime


def filter_error_log(record):
    return record["level"].name == "ERROR"


class Config(object):
    """Config for our app"""

    default = {
        "app": "callpy",
        "app_api_host": "127.0.0.1",
        "app_api_port": 8005,
        "alive": True,
        "wait_shutdown": False,
        "console_log": True,
        "mock_api_request": True,
        "oper_dispatcher_host": "127.0.0.1",
        "oper_dispatcher_port": 8090,
        "db_buffer_host": "127.0.0.1",
        "db_buffer_port": 7005,
        "demo_log": True,
        "call_direct_addresses": [
            "127.0.0.1:8200",
            "127.0.0.1:8201"
        ]
    }

    def __init__(self, config_path: str = ''):
        """
        Create new config

        @param config_path: File path with configs
        @return None.
        """
        join_config = {}
        if config_path and os.path.isfile(config_path):
            with open(config_path, "r") as jsonfile:
                join_config = json.load(jsonfile)
        else:
            print('WARNING! Config path not found => The default configuration will be used')

        self.log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>[<level>{level}</level>]" \
                          "<cyan>[{extra[object_id]}]</cyan>" \
                          "<magenta>{name}</magenta>:<magenta>{function}</magenta>:" \
                          "<cyan>{line}</cyan> - <level>{message}</level>"

        self.join_config: dict = join_config
        self.app_version: str = self.get_app_version()
        self.python_version: str = platform.python_version()
        self.uptime: datetime = datetime.now()

        self.new_config: dict = self.default.copy()
        self.new_config.update(join_config)
        self.alive: bool = bool(self.new_config['alive'])  # if true then start kill FastAPI and APP
        self.wait_shutdown: bool = bool(self.new_config['wait_shutdown'])  # if true then waiting for finish all tasks
        self.console_log: int = bool(self.new_config['console_log'])  # enable/disable log in console

        self.app: str = str(self.new_config['app'])
        self.app_api_host: str = str(self.new_config['app_api_host'])
        self.app_api_port: int = int(self.new_config['app_api_port'])

        self.mock_api_request: bool = bool(self.new_config['mock_api_request'])

        self.oper_dispatcher_host: str = str(self.new_config['oper_dispatcher_host'])
        self.oper_dispatcher_port: int = int(self.new_config['oper_dispatcher_port'])

        self.db_buffer_host: str = str(self.new_config['db_buffer_host'])
        self.db_buffer_port: int = int(self.new_config['db_buffer_port'])

        self.demo_log: list = bool(self.new_config['demo_log'])

        self.call_direct_addresses: list = list(self.new_config['call_direct_addresses'])

    def get_different_type_variables(self) -> list:
        different: list[str] = []
        for variable in self.new_config:
            new_type = type(self.default[variable])
            if variable not in self.default:
                different.append(f'not found config variable with name: {variable}')
            elif isinstance(self.new_config[variable], type(self.default[variable])) is False:
                different.append(f'{variable}: wrong={new_type}, right={type(self.new_config[variable])}')
        return different

    @staticmethod
    def get_app_version():
        if os.path.isfile('version'):
            f = open('version')
            return f.readline()
        else:
            print('WARNING! Not found file version, use version = 1.0.0')
            return '1.0.0'


if __name__ == "__main__":
    c = Config()
    print(c.alive)
