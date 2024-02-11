from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class ApiRequest(object):
    url: str
    method: str
    api_id: str = field(default_factory=lambda: str(uuid4().hex))
    request: dict = None
    timeout: int = None
    debug_log: bool = True
    headers: dict = field(default_factory=lambda: dict())
    correct_http_code: set = (200, 201, 202, 204, 404)
    attempts: int = 3
    duration_warning: int = 1

    def __post_init__(self):
        self.headers['x-api-id'] = self.api_id

    def __str__(self):
        self_dict = self.__dict__.copy()
        if len(str(self_dict['request'])) > 1000:
            self_dict['request'] = f"len={len(str(self.request))}"

        return str(self_dict)


if __name__ == "__main__":
    ar = ApiRequest(url='http://example.com', method='POST', request={"action": "test"})
    print(ar)
