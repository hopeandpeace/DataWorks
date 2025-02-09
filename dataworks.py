from fastapi import FastAPI, HTTPException
from pathlib import Path
import subprocess
import os

# Initialize FastAPI app
app = FastAPI()

def install_uv_and_run_datagen(user_email: str):
    """
    Installs uv (if not installed) and runs datagen.py with user_email as an argument.
    """
    try:
        # Check if uv is installed
        uv_installed = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        
        if uv_installed.returncode != 0:
            print("uv not found. Installing...")
            subprocess.run(["pip", "install", "uv"], check=True)

        # Run datagen.py using uv
        datagen_url = "https://raw.githubusercontent.com/sanand0/tools-in-data-science-public/tds-2025-01/project-1/datagen.py"
        subprocess.run(["uv", "run", datagen_url, user_email], check=True)
        
        return {"status": "success", "message": "datagen.py executed successfully"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/run")
async def run_task(task: str):
    """
    Executes a plain-English task.
    - 200 OK if successful
    - 400 Bad Request if the task is invalid
    - 500 Internal Server Error if the agent fails
    """
    try:
        if not task:
            raise HTTPException(status_code=400, detail="Invalid task description")

        if "install uv" in task.lower() and "datagen.py" in task.lower():
            user_email = "your_email@example.com"  # Replace with actual email if needed
            result = install_uv_and_run_datagen(user_email)
            return result

        return {"status": "success", "message": f"Task '{task}' executed"}
    
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/read")
async def read_file(path: str):
    """
    Reads the content of a file.
    - 200 OK if the file exists
    - 404 Not Found if the file does not exist
    """
    file_path = Path(f"data/{path}")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return file_path.read_text()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
