from locust import HttpUser, task, between

class QuickUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def view_home(self):
        self.client.get("/")

    @task(1)
    def view_post_1(self):
        # Ajuste '?p=1' para o id real do post que você criou (ou use a URL completa)
        self.client.get("/?p=1", name="post_1")
