import _grpc_runtime
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

grpc = _grpc_runtime.load_grpcio()
import inventory_pb2
import inventory_pb2_grpc

app = FastAPI()

INVENTORY_TARGET = "127.0.0.1:50051"
INVENTORY_DEADLINE_SECONDS = 1.0

_channel = grpc.insecure_channel(INVENTORY_TARGET)
_stub = inventory_pb2_grpc.InventoryServiceStub(_channel)


class OrderRequest(BaseModel):
    item_id: str
    quantity: int

    @field_validator("item_id")
    @classmethod
    def item_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("item_id is required")
        return value


def invalid_request(details: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_request", "details": details},
    )


@app.exception_handler(RequestValidationError)
async def validation_error(_request, exc: RequestValidationError):
    details = "item_id and quantity are required"
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", ())]
        message = str(err.get("msg", ""))
        if "item_id" in loc and "item_id is required" in message:
            details = "item_id is required"
            break
    return invalid_request(details)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/orders")
def place_order(body: OrderRequest):
    request = inventory_pb2.CheckInventoryRequest(
        item_id=body.item_id,
        quantity=body.quantity,
    )
    try:
        _stub.CheckInventory(request, timeout=INVENTORY_DEADLINE_SECONDS)
    except grpc.RpcError as error:
        return grpc_failure(error, body)

    return JSONResponse(
        status_code=201,
        content={
            "status": "accepted",
            "item_id": body.item_id,
            "quantity": body.quantity,
        },
    )


def grpc_failure(error, body: OrderRequest) -> JSONResponse:
    code = error.code()
    if code == grpc.StatusCode.NOT_FOUND:
        return JSONResponse(
            status_code=404,
            content={
                "error": "item_not_found",
                "item_id": body.item_id,
                "quantity": body.quantity,
            },
        )
    if code == grpc.StatusCode.FAILED_PRECONDITION:
        return JSONResponse(
            status_code=409,
            content={
                "error": "insufficient_stock",
                "available": int(error.details()),
                "requested": body.quantity,
            },
        )
    if code == grpc.StatusCode.INVALID_ARGUMENT:
        return invalid_request(error.details())
    if code == grpc.StatusCode.DEADLINE_EXCEEDED:
        return JSONResponse(status_code=504, content={"error": "inventory_timeout"})
    return JSONResponse(
        status_code=503,
        content={"error": "inventory_unavailable"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5002)
