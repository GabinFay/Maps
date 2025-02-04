# Use the official Python 3.13.0-slim image from the Docker Hub
FROM python:3.13.0-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port that Streamlit will run on
EXPOSE 8501

# Command to run the Streamlit app
CMD ["streamlit", "run", "maps_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
