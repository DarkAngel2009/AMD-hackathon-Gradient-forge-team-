"""Scaffold Generator — generates project structure, FastAPI starter, Dockerfile, and deploy config."""


def _folder_tree(arch_name: str) -> str:
    """Return a proposed folder structure string."""
    base = {
        "Monolith": """project/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI entry point
│   ├── config.py           # Settings & env vars
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py      # Pydantic models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── core.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── business_logic.py
│   └── database/
│       ├── __init__.py
│       └── connection.py
├── tests/
│   └── test_core.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md""",
        "Microservices": """project/
├── gateway/
│   ├── app/
│   │   ├── main.py         # API Gateway (FastAPI)
│   │   └── config.py
│   ├── Dockerfile
│   └── requirements.txt
├── auth-service/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   └── routes.py
│   ├── Dockerfile
│   └── requirements.txt
├── core-service/
│   ├── app/
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── routes.py
│   │   └── events.py
│   ├── Dockerfile
│   └── requirements.txt
├── notification-service/
│   ├── app/
│   │   ├── main.py
│   │   └── consumer.py
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── k8s/
│   ├── gateway-deployment.yaml
│   ├── core-deployment.yaml
│   └── namespace.yaml
└── README.md""",
        "Event-Driven": """project/
├── api/
│   ├── app/
│   │   ├── main.py         # FastAPI command API
│   │   ├── commands.py
│   │   └── events.py
│   ├── Dockerfile
│   └── requirements.txt
├── event-store/
│   ├── app/
│   │   ├── main.py
│   │   ├── store.py
│   │   └── projections.py
│   ├── Dockerfile
│   └── requirements.txt
├── workers/
│   ├── notification_worker/
│   │   ├── main.py
│   │   └── consumer.py
│   └── analytics_worker/
│       ├── main.py
│       └── consumer.py
├── docker-compose.yml
├── k8s/
│   ├── api-deployment.yaml
│   └── kafka-statefulset.yaml
└── README.md""",
        "Serverless": """project/
├── functions/
│   ├── auth/
│   │   └── handler.py
│   ├── core/
│   │   └── handler.py
│   ├── notifications/
│   │   └── handler.py
│   └── shared/
│       ├── models.py
│       └── utils.py
├── infrastructure/
│   ├── serverless.yml       # Serverless Framework config
│   └── terraform/
│       ├── main.tf
│       ├── api_gateway.tf
│       └── dynamodb.tf
├── tests/
│   └── test_handlers.py
├── requirements.txt
└── README.md""",
    }
    return base.get(arch_name, base["Monolith"])


def _fastapi_starter(system_desc: str) -> str:
    return f'''"""Auto-generated FastAPI starter for: {system_desc}"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="Generated API",
    description="{system_desc}",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthResponse(BaseModel):
    status: str
    service: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", service="core")


class ItemCreate(BaseModel):
    name: str
    description: str = ""


class ItemResponse(BaseModel):
    id: int
    name: str
    description: str


# In-memory store for prototype
_items: list[dict] = []


@app.post("/items", response_model=ItemResponse, status_code=201)
async def create_item(item: ItemCreate):
    new_item = {{"id": len(_items) + 1, **item.model_dump()}}
    _items.append(new_item)
    return ItemResponse(**new_item)


@app.get("/items", response_model=list[ItemResponse])
async def list_items():
    return [ItemResponse(**i) for i in _items]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''


def _dockerfile() -> str:
    return """FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""


def _deployment_config(arch_name: str) -> str:
    name_slug = arch_name.lower().replace("-", "").replace(" ", "-")
    return f"""# Kubernetes Deployment — {arch_name}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name_slug}-app
  labels:
    app: {name_slug}
spec:
  replicas: 2
  selector:
    matchLabels:
      app: {name_slug}
  template:
    metadata:
      labels:
        app: {name_slug}
    spec:
      containers:
        - name: {name_slug}
          image: {name_slug}-app:latest
          ports:
            - containerPort: 8000
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: {name_slug}-svc
spec:
  selector:
    app: {name_slug}
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
"""


def generate_scaffold(architecture_name: str, system_description: str) -> dict[str, str]:
    """Return a dict of filename -> content for the scaffold."""
    return {
        "folder_structure.txt": _folder_tree(architecture_name),
        "main.py": _fastapi_starter(system_description),
        "Dockerfile": _dockerfile(),
        "deployment.yaml": _deployment_config(architecture_name),
    }
