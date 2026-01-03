FROM public.ecr.aws/lambda/python:3.11

# Set build arguments for faster builds
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_DEFAULT_TIMEOUT=100

# Install dependencies with optimizations
COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --timeout=100 -r requirements.txt -t ${LAMBDA_TASK_ROOT}

# Copy application code (exclude unnecessary files via .dockerignore)
COPY . ${LAMBDA_TASK_ROOT}

# Set the CMD to the workflow handler
CMD [ "workflow_lambda_handler.handler" ]

