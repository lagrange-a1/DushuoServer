from dushuoserver.app import app

import uvicorn

if __name__ == "__main__":

    uvicorn.run("dushuoserver.app:app", host="0.0.0.0", port=8000, reload=True)
