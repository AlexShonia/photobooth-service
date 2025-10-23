from fastapi import FastAPI, File, Form, UploadFile

from printer import print_image
from pos import run_pos_payment

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/print-images/")
async def print_images(
    image: UploadFile = File(...),
    amount: int = Form(...),
):
    image_bytes = await image.read()

    for _ in range(amount):
        print_image(image_bytes)

    return {"status": "success"}


@app.post("/pos-terminal-payment/")
async def pos_terminal_payment(amount: float):
    result = run_pos_payment(amount)

    return {"status": "success"}
