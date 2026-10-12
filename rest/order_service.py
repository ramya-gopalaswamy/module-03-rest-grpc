import os

import requests
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

app = FastAPI()

INVENTORY_URL = os.environ.get(
    "INVENTORY_URL", "http://127.0.0.1:5001/inventory/check"
)
INVENTORY_TIMEOUT_SECONDS = 1.0


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
    if body.quantity < 1:
        return invalid_request("quantity must be at least 1")

    try:
        inventory_response = requests.post(
            INVENTORY_URL,
            json={"item_id": body.item_id, "quantity": body.quantity},
            timeout=INVENTORY_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        return JSONResponse(status_code=504, content={"error": "inventory_timeout"})
    except requests.RequestException:
        return JSONResponse(status_code=503, content={"error": "inventory_unavailable"})

    if inventory_response.status_code == 200:
        return JSONResponse(
            status_code=201,
            content={
                "status": "accepted",
                "item_id": body.item_id,
                "quantity": body.quantity,
            },
        )

    return JSONResponse(
        status_code=inventory_response.status_code,
        content=inventory_response.json(),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=5000)
