import os
import time

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

app = FastAPI()

STOCK = {
    "apple": 10,
    "banana": 2,
}


class CheckRequest(BaseModel):
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


@app.post("/inventory/check")
def check_inventory(body: CheckRequest):
    delay_ms = int(os.environ.get("INVENTORY_DELAY_MS", "0"))
    if delay_ms > 0:
        time.sleep(delay_ms / 1000)

    if body.quantity < 1:
        return invalid_request("quantity must be at least 1")

    if body.item_id not in STOCK:
        return JSONResponse(
            status_code=404,
            content={
                "error": "item_not_found",
                "item_id": body.item_id,
                "quantity": body.quantity,
            },
        )

    in_stock = STOCK[body.item_id]
    if body.quantity > in_stock:
        return JSONResponse(
            status_code=409,
            content={
                "error": "insufficient_stock",
                "available": in_stock,
                "requested": body.quantity,
            },
        )

    return {"item_id": body.item_id, "available": in_stock}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5001)
