from fastapi import FastAPI, HTTPException
from pathlib import Path

# Initialize FastAPI app
app = FastAPI()

@app.post("/run")
async def run_task(task: str):
    """
    Executes a plain-English task.
    Returns:
    - 200 OK if successful
    - 400 Bad Request if the task is invalid
    - 500 Internal Server Error if the agent fails
    """
    try:
        if not task:
            raise HTTPException(status_code=400, detail="Invalid task description")

        # TODO: Add logic to process the task here

        return {"status": "success", "message": f"Task '{task}' executed"}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/read")
async def read_file(path: str):
    """
    Reads the content of a file.
    Returns:
    - 200 OK if the file exists
    - 404 Not Found if the file does not exist
    """
    file_path = Path(f"data/{path}").resolve()
    print(f"Trying to read: {file_path}")  # Debugging line
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return file_path.read_text()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
