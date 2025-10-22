from typing import Union

from fastapi import FastAPI, File, Form, UploadFile

from printer import print_image

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
        print_image(image_bytes, amount)

    return {"status": "success"}


@app.post("/pos-terminal-payment/")
async def pos_terminal_payment():

    return {"status": "success"}
