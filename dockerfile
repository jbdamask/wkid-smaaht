# Use a Fargate-compatible Python 3.10.9 slim-buster base image for the desired architecture
# For x86_64:
FROM python:3.10.9-slim-buster AS x86_base

# For ARM64:
# FROM --platform=linux/arm64 python:3.10.9-slim-buster AS arm64_base

# Set the working directory in the container to /app
WORKDIR /app

# Add the src directory contents into the container at /app
ADD src/ /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Run chataws.py when the container launches
CMD ["python", "chataws.py"]
