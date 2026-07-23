from fastapi import FastAPI


app = FastAPI(
    version="0.1.0",
    title="Restaurant ERP Template",
)


@app.get("/")
async def health():
    return {"detail": "ok"}
