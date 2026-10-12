import os
import time
from concurrent import futures

import _grpc_runtime

grpc = _grpc_runtime.load_grpcio()
import inventory_pb2
import inventory_pb2_grpc

STOCK = {
    "apple": 10,
    "banana": 2,
}


class InventoryService(inventory_pb2_grpc.InventoryServiceServicer):
    def CheckInventory(self, request, context):
        delay_ms = int(os.environ.get("INVENTORY_DELAY_MS", "0"))
        if delay_ms > 0:
            time.sleep(delay_ms / 1000)

        if request.quantity < 1:
            context.abort(
                grpc.StatusCode.INVALID_ARGUMENT,
                "quantity must be at least 1",
            )

        item_id = request.item_id
        if not item_id.strip():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "item_id is required")

        if item_id not in STOCK:
            context.abort(grpc.StatusCode.NOT_FOUND, "item_not_found")

        available = STOCK[item_id]
        if request.quantity > available:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(available))

        return inventory_pb2.CheckInventoryResponse(
            item_id=item_id,
            available=available,
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(
        InventoryService(),
        server,
    )
    server.add_insecure_port("127.0.0.1:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
