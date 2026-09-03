import grpc

from yc_watcher.errors import describe_error


class FakeRpcError(grpc.RpcError):
    def __init__(self, code, details):
        self._code = code
        self._details = details

    def code(self):
        return self._code

    def details(self):
        return self._details


def test_rpc_error_renders_code_and_details():
    error = FakeRpcError(grpc.StatusCode.PERMISSION_DENIED, "no access to folder")
    assert describe_error(error) == "PERMISSION_DENIED: no access to folder"


def test_rpc_error_without_details_renders_code_only():
    error = FakeRpcError(grpc.StatusCode.UNAVAILABLE, "")
    assert describe_error(error) == "UNAVAILABLE"


def test_plain_exception_renders_type_and_message():
    assert describe_error(ValueError("bad thing")) == "ValueError: bad thing"
