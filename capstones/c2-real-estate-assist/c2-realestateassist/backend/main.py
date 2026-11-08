from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from start import real_estate_main
import uvicorn
from start.real_estate_main import router as BotRouter

app = FastAPI(
    title="Real Estate Asisstant..",
    description="Agent LCEL chain Router",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(BotRouter)





def main():
    print("Hello from backend!")
    uvicorn.run(app, host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
