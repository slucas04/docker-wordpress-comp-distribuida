from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def view_home(self):
        self.client.get("/")

    @task(6)
    def view_large_text_post(self):
        # ajuste ?p=<ID> para o ID do post com ~400KB de texto
        self.client.get("/?p=2", name="post_large_text")
