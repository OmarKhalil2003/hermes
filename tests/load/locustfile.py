import random

from locust import HttpUser, between, task


class HermesLoadTestUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def health_check(self) -> None:
        """Simulates checking system health endpoints."""
        self.client.get("/healthz")

    @task(2)
    def check_metrics(self) -> None:
        """Simulates prometheus metrics scraping endpoints."""
        self.client.get("/metrics")

    @task(3)
    def search_query(self) -> None:
        """Simulates users executing RAG search queries."""
        queries = [
            "LLM fine-tuning",
            "agentic workflows",
            "vector indexing",
            "Hermes documentation",
        ]
        query = random.choice(queries)
        self.client.get(f"/api/v1/search?query={query}", name="/api/v1/search")

    @task(1)
    def check_active_deployment(self) -> None:
        """Simulates checking active model deployment routing status."""
        self.client.get(
            "/api/v1/jobs/deployments/active",
            name="/api/v1/jobs/deployments/active",
        )
