from dataclasses import dataclass


@dataclass
class ApiResponse(object):
    http_code: int
    execute_time: int
    net_status: bool
    success: bool
    message: str
    result: dict | None
    content_type: str = 'application/json'
    used_attempts: int = 0

    def __str__(self):
        self_dict = self.__dict__.copy()
        if len(str(self_dict['result'])) > 1000:
            self_dict['result'] = f"len={len(str(self.result))}"

        return str(self_dict)


if __name__ == "__main__":
    ar = ApiResponse(http_code=0, execute_time=0, net_status=False, success=False, message='', result=None)
    print(ar)
