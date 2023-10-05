# Use a Fargate-compatible Python 3.10.9 slim-buster base image for the desired architecture
# For x86_64:
FROM python:3.10.9-slim-buster AS x86_base

# For ARM64:
# FROM --platform=linux/arm64 python:3.10.9-slim-buster AS arm64_base

# Set the working directory in the container to /app
WORKDIR /app

# Copy the requirements.txt file to the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Add the src directory and gpt4_system_prompts contents into the container at /app
# COPY src/ gpt4_system_prompts/ chat_with_docs/ /app/

COPY src/ /app/src/
COPY gpt4_system_prompts/ /app/gpt4_system_prompts/
COPY chat_with_docs/ /app/chat_with_docs/
COPY wkid_smaaht.py /app/

# Set PYTHONUNBUFFERED environment variable
ENV PYTHONUNBUFFERED=1

# Run chataws.py when the container launches
CMD ["python", "wkid_smaaht.py"]
