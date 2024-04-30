FROM python:3.8-slim
WORKDIR /app
COPY requirements.txt .

# Install dependencies for numpy
RUN pip3 install --upgrade pip
RUN pip3 install Cython Cmake

# Install pip packages from requirements.txt
RUN pip3 install -r ./requirements.txt
COPY . .
