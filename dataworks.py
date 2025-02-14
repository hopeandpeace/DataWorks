from fastapi import FastAPI, HTTPException, Request, Body
from pathlib import Path
import subprocess
import os
import datetime
import requests
import re
import json

# Initialize FastAPI app
app = FastAPI()

def install_uv_and_run_datagen(user_email: str):
    """Installs uv (if not installed) and runs datagen.py with user_email as an argument."""
    try:
        uv_installed = subprocess.run(["uv", "--version"], capture_output=True, text=True)

        if uv_installed.returncode != 0:
            print("uv not found. Installing...")
            subprocess.run(["pip", "install", "uv"], check=True)

        datagen_url = "https://raw.githubusercontent.com/sanand0/tools-in-data-science-public/tds-2025-01/project-1/datagen.py"
        subprocess.run(["uv", "run", datagen_url, user_email], check=True)

        return {"status": "success", "message": "datagen.py executed successfully"}
    
    except Exception as e:
        return {"status": "error", "message": f"Datagen failed: {e}"}

def format_markdown_file():
    """Formats /data/format.md using Prettier."""
    try:
        file_path = Path("data/format.md")

        if not file_path.exists():
            return {"status": "error", "message": "File not found: /data/format.md"}

        subprocess.run(["npx.cmd", "prettier", "--write", str(file_path)], check=True)

        return {"status": "success", "message": "Markdown file formatted successfully"}

    except Exception as e:
        return {"status": "error", "message": f"Markdown formatting failed: {e}"}

def detect_if_counting(task_text):
    """Detects if the task is asking to count occurrences of a weekday."""
    api_key = os.environ["AIPROXY_TOKEN"]
    proxy_url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that understands all languages."},
            {"role": "user", "content": f'''
                The following task may be written in any language.
                Your job is to determine if it is asking to count occurrences of a weekday.

                - If the task is about counting a weekday, respond only with "yes".
                - If it is NOT about counting a weekday, respond only with "no".
                - Do NOT explain your answer. Do NOT add extra words.

                Task: "{task_text}"
            '''}
        ]

    }

    try:
        response = requests.post(proxy_url, headers=headers, json=data)
        response_json = response.json()
        return response_json["choices"][0]["message"]["content"].strip().lower() == "yes"

    except Exception as e:
        print(f"⚠️ AI Proxy Error: in detect_if_counting: {e}")
        return False

def detect_weekday(task_text):
    #Extracts the weekday from the task description and translates it to English.
    prompt = f"""
    Extract the day of the week (Monday, Tuesday, etc.) from this text, regardless of the language:
    "{task_text}"
    Respond with only the English weekday name.
    """
    api_key = os.environ["AIPROXY_TOKEN"]
    proxy_url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(proxy_url, headers=headers, json=data)
        response_json = response.json()
        weekday = response_json["choices"][0]["message"]["content"].strip().lower()

        valid_weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        return weekday if weekday in valid_weekdays else None

    except Exception as e:
        print(f"⚠️ AI Proxy Error: {e}")
        return None

def count_weekday_in_file(input_file, day_name, output_file):
    """Counts the occurrences of a specific weekday in a file (dates must be in YYYY-MM-DD format)."""
    try:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            return {"status": "error", "message": f"File not found: {input_file}"}

        with open(input_path, "r") as f:
            lines = f.readlines()

        count = 0
        for line in lines:
            try:
                # ✅ Extract the first date (YYYY-MM-DD) from each line
                match = re.search(r"\d{4}-\d{2}-\d{2}", line)
                if not match:
                    continue  # Skip lines without valid dates

                date_obj = datetime.datetime.strptime(match.group(), "%Y-%m-%d")
                actual_weekday = date_obj.strftime("%A").lower()

                if actual_weekday == day_name.lower():
                    count += 1
            except ValueError:
                continue  

        with open(output_path, "w") as f:
            f.write(str(count))

        return {"status": "success", "message": f"Counted {count} {day_name}s in {input_file}."}

    except Exception as e:
        return {"status": "error", "message": f"Weekday counting failed: {e}"}

def sort_contacts(input_file, output_file):
    """Reads contacts from JSON, sorts them by last_name, then first_name, and writes to a new file."""
    try:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            return {"status": "error", "message": f"File not found: {input_file}"}

        # ✅ Read contacts from JSON file
        with open(input_path, "r") as f:
            contacts = json.load(f)

        # ✅ Sort by last_name, then first_name
        sorted_contacts = sorted(contacts, key=lambda x: (x["last_name"], x["first_name"]))

        # ✅ Write the sorted contacts back to a new JSON file
        with open(output_path, "w") as f:
            json.dump(sorted_contacts, f, indent=4)

        return {"status": "success", "message": f"Contacts sorted successfully into {output_file}."}

    except Exception as e:
        return {"status": "error", "message": f"Sorting contacts failed: {e}"}

@app.post("/run")
async def run_task(task: dict = Body(...)):
    """Handles all incoming tasks by detecting the required operation."""
    task_text = task.get("task", "")
    print(f"📝 Received task: {task_text}")

    try:
        if not task_text:
            raise HTTPException(status_code=400, detail="Invalid task description")

        # ✅ Handle Datagen Task
        if "install uv" in task_text.lower() and "datagen.py" in task_text.lower():
            user_email = "your_email@example.com"
            return install_uv_and_run_datagen(user_email)

        # ✅ Handle Markdown Formatting Task
        if "format" in task_text.lower() and "markdown" in task_text.lower():
            return format_markdown_file()

        # ✅ Extract input & output filenames and handle weekday counting task
        if detect_if_counting(task_text):  # ✅ This ensures it's a weekday counting task
            count_keywords = ["count", "find", "how many", "calculate"]
            found_count_keyword = any(keyword in task_text.lower() for keyword in count_keywords)

            if found_count_keyword:
                day_name = detect_weekday(task_text)
            else:
                is_counting_request = detect_if_counting(task_text)
                if not is_counting_request:
                    return {"status": "error", "message": "Task does not seem to be about counting weekdays"}
                day_name = detect_weekday(task_text)

            if not day_name:
                return {"status": "error", "message": "Could not determine the weekday from the task description"}
            
            input_file, output_file = None, None
            tokens = task_text.replace(",", "").split()

            for word in tokens:
                if word.startswith("/data/") and input_file is None:
                    input_file = os.path.normpath(word.lstrip("/"))
                elif word.startswith("/data/") and output_file is None:
                    output_file = os.path.normpath(word.lstrip("/"))

            if not input_file or not output_file:
                return {"status": "error", "message": "Could not extract file paths from task description"}

            print(f"📂 Extracted input file: {input_file}")
            print(f"📁 Extracted output file: {output_file}")
            print(f"📅 Extracted weekday: {day_name}")

            # ✅ Count occurrences of the weekday in the input file
            print("🚀 About to call count_weekday_in_file()...")
            result = count_weekday_in_file(input_file, day_name, output_file)
            print(f"✅ Function executed, result: {result}")

        if "sort" in task_text.lower() and "contacts" in task_text.lower():
            input_file = "data/contacts.json"
            output_file = "data/contacts-sorted.json"

            print(f"📂 Sorting contacts from {input_file} → {output_file}")
            
            result = sort_contacts(input_file, output_file)
            print(f"✅ Sorting complete: {result}")

            return result


        return result

    except Exception as e:
        return {"status": "error", "message": str(e)}

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
