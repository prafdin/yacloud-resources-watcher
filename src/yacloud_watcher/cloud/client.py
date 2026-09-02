import json

from yandex.cloud.compute.v1.instance_service_pb2_grpc import InstanceServiceStub
from yandex.cloud.vpc.v1.network_service_pb2_grpc import NetworkServiceStub
from yandexcloud import SDK


class YCClient:
    def __init__(self, service_account_key_file: str, folder_id: str):
        with open(service_account_key_file, "r") as f:
            service_account_key = json.load(f)

        self.sdk = SDK(service_account_key=service_account_key)
        self.folder_id = folder_id

    def instance_service(self):
        return self.sdk.client(InstanceServiceStub)

    def network_service(self):
        return self.sdk.client(NetworkServiceStub)
