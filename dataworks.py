from fastapi import FastAPI, HTTPException, Request, Body
from pathlib import Path
import subprocess
import os
import datetime
import requests
import copy
import re
import json
from PIL import Image
import base64
import easyocr
import numpy as np
from tqdm import tqdm
import sqlite3

# Initialize FastAPI app
app = FastAPI()

import requests
import os

def detect_task_with_llm(task_text):
    """Uses LLM to detect which task (A1-A10) is being requested."""
    api_key = os.getenv("AIPROXY_TOKEN")
    proxy_url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Match the given task to one from A1 to A10."},
            {"role": "user", "content": f"""
                A1: Install uv & run datagen.py.
                A2: Format markdown with prettier@3.4.2.
                A3: Count specific weekdays in input file & write to output.
                A4: Sort contacts in JSON by last_name, first_name & write output.
                A5: Write first lines of recent .log files to output.
                A6: Extract first H1 from all .md in /docs/ & write to index.json.
                A7: Extract sender's email from input text using LLM & write output.
                A8: Extract credit card number from image using OCR/LLM & write output.
                A9: Find most similar comments from input using embeddings & write output.
                A10: Calculate total sales of ticket type from SQLite DB & write output.
                Respond with ONLY the task number (A1, A2, A3, etc.).
                Task: "{task_text}"
            """}
        ]
    }

    try:
        response = requests.post(proxy_url, headers=headers, json=data)
        response_json = response.json()
        predicted_task = response_json["choices"][0]["message"]["content"].strip()
        print(f"🤖 LLM Detected Task: {predicted_task}")
        return predicted_task
    except Exception as e:
        print(f"⚠️ LLM Detection Error: {e}")
        return None

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

def format_markdown_file_dynamic(input_file: str, prettier_version: str = "latest"):
    """Formats the given Markdown file using Prettier with the specified version."""
    try:
        file_path = Path(input_file)

        if not file_path.exists():
            return {"status": "error", "message": f"File not found: {input_file}"}

        subprocess.run(["npx.cmd", f"prettier@{prettier_version}", "--write", str(file_path)], check=True)

        return {"status": "success", "message": f"Markdown file {input_file} formatted successfully using Prettier@{prettier_version}"}

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
    try:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            return {"status": "error", "message": f"File not found: {input_file}"}

        with open(input_path, "r") as f:
            lines = f.readlines()

        count = 0
        date_formats = [
            "%Y-%m-%d",      # 2006-06-05
            "%d-%b-%Y",      # 22-Aug-2000
            "%b %d, %Y",     # May 13, 2021
            "%Y/%m/%d %H:%M:%S"  # 2023/09/24 08:02:54
        ]

        for line in lines:
            line = line.strip()  # Remove spaces
            for fmt in date_formats:
                try:
                    date_obj = datetime.datetime.strptime(line, fmt)
                    actual_weekday = date_obj.strftime("%A").lower()

                    if actual_weekday == day_name.lower():
                        print(f"✅ Counting: {line} ({actual_weekday})")  # 👀 Debug output
                        count += 1
                    break  # ✅ Exit loop once a valid format is found
                except ValueError:
                    continue  # ❌ Try the next format if the current one fails

        with open(output_path, "w") as f:
            f.write(str(count))

        return {"status": "success", "message": f"Counted {count} {day_name}s in {input_file}."}

    except Exception as e:
        return {"status": "error", "message": f"Weekday counting failed: {e}"}

def sort_contacts_dynamic(input_file: str, output_file: str):
    """Reads contacts from a JSON file, sorts them by last_name then first_name, and writes to output file."""
    try:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            return {"status": "error", "message": f"File not found: {input_file}"}

        with open(input_path, "r", encoding="utf-8") as f:
            contacts = json.load(f)

        sorted_contacts = sorted(contacts, key=lambda x: (x["last_name"], x["first_name"]))

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(sorted_contacts, f, indent=4)

        return {"status": "success", "message": f"Contacts sorted successfully into {output_file}"}

    except Exception as e:
        return {"status": "error", "message": f"Sorting contacts failed: {e}"}

def write_recent_log_lines_dynamic(logs_dir: str, output_file: str):
    """Writes the first line of the 10 most recent .log files from a dynamic folder to a dynamic output file."""
    try:
        logs_path = Path(logs_dir)
        output_path = Path(output_file)

        if not logs_path.exists() or not logs_path.is_dir():
            return {"status": "error", "message": f"Logs directory not found: {logs_dir}"}

        log_files = sorted(
            logs_path.glob("*.log"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )[:10]

        first_lines = []
        for log_file in log_files:
            with open(log_file, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                first_lines.append(first_line)

        with open(output_path, "w", encoding="utf-8") as f:
            for line in first_lines:
                f.write(line + "\n")

        return {"status": "success", "message": f"Extracted first lines from {len(first_lines)} log files to {output_file}"}

    except Exception as e:
        return {"status": "error", "message": f"Failed to process logs: {e}"}
    
def extract_h1_titles(input_folder, output_file):
    """Extracts the first H1 title from each Markdown file in a folder and writes to a JSON index."""
    try:
        input_path = Path(input_folder)
        output_path = Path(output_file)

        if not input_path.exists() or not input_path.is_dir():
            return {"status": "error", "message": f"Folder not found: {input_folder}"}

        index = {}

        # ✅ Loop through all Markdown files (including subfolders)
        for md_file in input_path.rglob("*.md"):
            relative_path = md_file.relative_to(input_path)  # Get path *without* "/data/docs/"
            relative_str = str(relative_path).replace("\\", "/")  # Normalize path for JSON keys

            with open(md_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("# "):  # ✅ First H1 heading found
                        title = line.strip("# ").strip()
                        index[relative_str] = title  # Store using relative path
                        break  # ✅ Stop reading after the first H1

        # ✅ Write to output JSON file
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=4)

        return {"status": "success", "message": f"Extracted H1 titles into {output_file}."}

    except Exception as e:
        return {"status": "error", "message": f"H1 extraction failed: {e}"}
    
def extract_email_sender(input_file, output_file):
    """Extracts the sender's email using an LLM API and writes it to output_file."""
    try:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            return {"status": "error", "message": f"File not found: {input_file}"}

        # ✅ Read the email content
        with open(input_path, "r", encoding="utf-8") as f:
            email_content = f.read().strip()

        if not email_content:
            return {"status": "error", "message": "Email file is empty"}

        # ✅ Prepare API request for LLM
        api_key = os.environ["AIPROXY_TOKEN"]
        proxy_url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

        headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}

        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are an AI that extracts sender email addresses from emails."},
                {"role": "user", "content": f"""
                    Extract the sender's email address from this email content:
                    ----
                    {email_content}
                    ----
                    Respond with only the email address and nothing else.
                """}
            ]
        }

        # ✅ Send request to LLM
        response = requests.post(proxy_url, headers=headers, json=data)
        response_json = response.json()

        sender_email = response_json["choices"][0]["message"]["content"].strip()

        if "@" not in sender_email:  # Sanity check: Ensure it's an email
            return {"status": "error", "message": "LLM did not return a valid email"}

        # ✅ Write extracted email to the output file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(sender_email)

        return {"status": "success", "message": f"Extracted email saved to {output_file}"}

    except Exception as e:
        return {"status": "error", "message": f"Email extraction via LLM failed: {e}"}

def extract_credit_card_number(input_image: str, output_file: str):
    """Extracts credit card number using OCR and LLM, validates it, and writes it to a file."""
    input_path = Path(input_image)
    output_path = Path(output_file)


    if not input_path.exists():
        return {"status": "error", "message": f"Image file {input_path} does not exist."}

    reader = easyocr.Reader(['en'])
    try:
        result = reader.readtext(str(input_path))
        print(f"🖼️ Raw OCR output: {result}")

        # Extract all text from the OCR result
        extracted_texts = [text for (_, text, _) in result]
        extracted_text_str = " ".join(extracted_texts)

        # LLM prompt
        prompt = f"""
        The following text was extracted from an image using OCR. It may contain multiple numbers including dates, codes, and a credit card number.
        **Please extract ONLY the credit card number**, which is usually the first long numeric sequence, and return only that number without spaces or dashes.
        Ignore any dates or other numbers. If no valid credit card number is found, return "None".

        Extracted text: {extracted_text_str}
        """

        api_key = os.environ.get("AIPROXY_TOKEN")
        proxy_url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are an expert at processing and extracting numeric information from OCR results."},
                {"role": "user", "content": prompt}
            ]
        }

        # Send request to LLM
        response = requests.post(proxy_url, headers=headers, json=data)
        response_json = response.json()
        card_number = response_json["choices"][0]["message"]["content"].strip()

        # Validate the card number: 12-19 digits only
        if not re.fullmatch(r'\d{12,19}', card_number):
            return {"status": "error", "message": "No valid credit card number found in the image."}

        # Write to output file
        with open(output_path, "w") as f:
            f.write(card_number)

        return {"status": "success", "message": f"Credit card number extracted and written to {output_file}"}

    except Exception as e:
        return {"status": "error", "message": f"Failed to extract credit card number: {e}"}

def extract_embeddings(comments):
    """Extract embeddings for a list of comments using the AI Proxy API."""
    api_key = os.environ["AIPROXY_TOKEN"]
    proxy_url = "https://aiproxy.sanand.workers.dev/openai/v1/embeddings"
    
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}

    embeddings = []
    for comment in tqdm(comments, desc="Generating embeddings"):
        data = {
            "model": "text-embedding-3-small",
            "input": comment
        }
        
        try:
            response = requests.post(proxy_url, headers=headers, json=data)
            response_json = response.json()
            embedding = response_json["data"][0]["embedding"]
            embeddings.append(np.array(embedding))
        except Exception as e:
            raise ValueError(f"Failed to generate embeddings: {e}")

    return embeddings

def cosine_similarity(vec1, vec2):
    """Calculate the cosine similarity between two vectors."""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def find_most_similar_comments(input_file, output_file):
    """Find the most similar pair of comments using embeddings and write to output."""
    try:
        input_path = Path(input_file)
        output_path = Path(output_file)

        if not input_path.exists():
            return {"status": "error", "message": f"File not found: {input_file}"}

        with open(input_path, "r", encoding="utf-8") as f:
            comments = [line.strip() for line in f.readlines() if line.strip()]

        if len(comments) < 2:
            return {"status": "error", "message": "Not enough comments to compare"}

        embeddings = extract_embeddings(comments)

        max_sim = -1
        pair = ("", "")
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                if sim > max_sim:
                    max_sim = sim
                    pair = (comments[i], comments[j])

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(pair[0] + "\n" + pair[1])

        return {"status": "success", "message": f"Most similar comments written to {output_file}"}

    except Exception as e:
        return {"status": "error", "message": f"Failed to find similar comments: {e}"}

def calculate_gold_ticket_sales():
    """Calculates total sales for 'Gold' ticket type and writes to output file."""
    try:
        db_path = Path("data/ticket-sales.db")
        output_path = Path("data/ticket-sales-gold.txt")

        if not db_path.exists():
            return {"status": "error", "message": "Database file not found"}

        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute query to calculate total sales for 'Gold' ticket type
        cursor.execute("SELECT SUM(units * price) FROM tickets WHERE type = 'Gold'")
        total_sales = cursor.fetchone()[0]  # Fetch the result

        if total_sales is None:
            total_sales = 0  # If no 'Gold' tickets, total sales is 0

        # Write the total sales to the output file
        with open(output_path, "w") as f:
            f.write(str(total_sales))

        conn.close()
        return {"status": "success", "message": f"Total sales for 'Gold' tickets written to {output_path}"}

    except Exception as e:
        return {"status": "error", "message": f"Failed to calculate gold ticket sales: {e}"}

@app.post("/run")
async def run_task(task: dict = Body(...)):
    """Handles all incoming tasks by detecting the required operation."""
    task_text = task.get("task", "")
    print(f"📝 Received task: {task_text}")

    task_number = detect_task_with_llm(task_text)
    if not task_number:
        return {"status": "error", "message": "Failed to detect task with LLM"}

    print(f"🔍 Detected Task: {task_number}")

    try:
        if not task_text:
            raise HTTPException(status_code=400, detail="Invalid task description")

        # ✅ Datagen Task
        if task_number=="A1":
            user_email = "23f2000057@ds.study.iitm.ac.in"
            return install_uv_and_run_datagen(user_email)

        # ✅ Markdown Formatting Task
        if task_number == "A2":
            input_file, prettier_version = None, "latest"
            tokens = task_text.replace(",", "").split()

            for word in tokens:
                if word.startswith("/data/") and word.endswith(".md"):
                    input_file = os.path.normpath(word.lstrip("/"))
                if "prettier@" in word:
                    prettier_version = word.split("@")[-1]

            if not input_file:
                return {"status": "error", "message": "Could not extract input Markdown file path from task description"}

            print(f"📂 Formatting {input_file} using Prettier version {prettier_version}")
            result = format_markdown_file_dynamic(input_file, prettier_version)
            print(f"✅ Markdown formatting complete: {result}")

            return result

        # ✅ Weekday counting task
        if task_number=="A3":
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

        # ✅ Sorting contacts task
        if task_number == "A4":
            input_file, output_file = None, None
            tokens = task_text.replace(",", "").split()

            for word in tokens:
                if word.startswith("/data/") and word.endswith(".json") and input_file is None:
                    input_file = os.path.normpath(word.lstrip("/"))
                elif word.startswith("/data/") and word.endswith(".json") and output_file is None:
                    output_file = os.path.normpath(word.lstrip("/"))

            if not input_file or not output_file:
                return {"status": "error", "message": "Could not extract input or output JSON file paths from task description"}

            print(f"📂 Sorting contacts from {input_file} → {output_file}")
            result = sort_contacts_dynamic(input_file, output_file)
            print(f"✅ Sorting complete: {result}")

            return result
        
        # ✅ Extract recent log lines task
        if task_number == "A5":
            logs_dir, output_file = None, None
            tokens = task_text.replace(",", "").split()

            for word in tokens:
                if word.startswith("/data/") and word.endswith("/"):
                    logs_dir = os.path.normpath(word.lstrip("/"))
                elif word.startswith("/data/") and word.endswith(".txt"):
                    output_file = os.path.normpath(word.lstrip("/"))

            if not logs_dir or not output_file:
                return {"status": "error", "message": "Could not extract log directory or output file path from task description"}

            print(f"📂 Extracting first lines of the 10 most recent log files from {logs_dir} → {output_file}")
            result = write_recent_log_lines_dynamic(logs_dir, output_file)
            print(f"✅ Log processing complete: {result}")

            return result
        
        # ✅ First H1 in markdown files task
        if task_number=="A6":
            input_folder, output_file = None, None
            tokens = task_text.replace(",", "").split()

            for word in tokens:
                if word.startswith("/data/") and word.endswith("/"):
                    input_folder = os.path.normpath(word.lstrip("/"))
                elif word.startswith("/data/") and word.endswith(".json"):
                    output_file = os.path.normpath(word.lstrip("/"))

            if not input_folder or not output_file:
                return {"status": "error", "message": "Could not extract folder or output file paths from task description"}

            print(f"📂 Extracting H1 titles from Markdown files in {input_folder} → {output_file}")
            result = extract_h1_titles(input_folder, output_file)
            print(f"✅ Extraction complete: {result}")

            return result
        
        # ✅ Email sender extraction task
        if task_number=="A7":
            input_file, output_file = None, None
            tokens = task_text.replace(",", "").split()

            for word in tokens:
                if word.endswith(".txt") and word.startswith("/data/"):
                    if input_file is None:
                        input_file = os.path.normpath(word.lstrip("/"))
                    else:
                        output_file = os.path.normpath(word.lstrip("/"))

            if not input_file or not output_file:
                return {"status": "error", "message": "Could not extract file paths from task description"}

            print(f"📂 Extracting sender email using LLM from {input_file} → {output_file}")
            result = extract_email_sender(input_file, output_file)
            print(f"✅ Email extraction complete: {result}")

            return result
        
        # ✅ Credit card number extraction task
        if task_number=="A8":
            input_file, output_file = None, None
            tokens = task_text.replace(",", "").split()

            for word in tokens:
                if word.endswith(".png") and word.startswith("/data/"):
                    input_file = os.path.normpath(word.lstrip("/"))
                elif word.endswith(".txt") and word.startswith("/data/"):
                    output_file = os.path.normpath(word.lstrip("/"))

            if not input_file or not output_file:
                return {"status": "error", "message": "Could not extract file paths from task description"}

            print(f"📂 Extracting credit card number from {input_file} → {output_file}")
            result = extract_credit_card_number(input_file, output_file)
            print(f"✅ Credit card extraction complete: {result}")

            return result

        # ✅ Similar pair of comments task
        if task_number=="A9":
            # Extract input and output files from task_text
            tokens = task_text.replace(",", "").split()
            input_file, output_file = None, None

            for word in tokens:
                if word.startswith("/data/") and input_file is None:
                    input_file = os.path.normpath(word.lstrip("/"))
                elif word.startswith("/data/") and output_file is None:
                    output_file = os.path.normpath(word.lstrip("/"))

            if not input_file or not output_file:
                return {"status": "error", "message": "Could not extract input/output file paths from task description"}

            print(f"📂 Finding most similar comments from {input_file} → {output_file}")
            result = find_most_similar_comments(input_file, output_file)
            print(f"✅ Similar comments found: {result}")

            return result

        # ✅ Details from SQLite database file task
        if task_number=="A10":
            print("📂 Calculating total sales for 'Gold' tickets...")
            result = calculate_gold_ticket_sales()
            print(f"✅ Ticket sales calculation complete: {result}")
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
