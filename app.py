from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import uuid
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

# Connect to MongoDB (cloud DB)
mongo_url = os.getenv("MONGO_URL")
client = MongoClient(mongo_url)
db = client["sandbox_db"]
collection = db["submissions"]

# Request model
class CodeRequest(BaseModel):
    code: str

@app.get("/")
def home():
    return {"message": "Cloud Code Sandbox Running"}

@app.post("/run")
def run_code(request: CodeRequest):
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}.py"

    # Save user code temporarily
    with open(filename, "w") as f:
        f.write(request.code)

    try:
        # Run inside Docker container
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--network", "none",
                "-m", "100m",
                "--cpus", "0.5",
                "-v", f"{os.getcwd()}:/app",
                "python:3.10",
                "python", f"/app/{filename}"
            ],
            capture_output=True,
            text=True,
            timeout=5
        )

        output = result.stdout
        error = result.stderr

    except subprocess.TimeoutExpired:
        output = ""
        error = "Execution timed out"

    # Remove file
    os.remove(filename)

    # Store in database
    collection.insert_one({
        "code": request.code,
        "output": output,
        "error": error
    })

    return {"output": output, "error": error}
