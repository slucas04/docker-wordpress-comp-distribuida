from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task(2)
    def view_home(self):
        self.client.get("/")

    @task(5)
    def view_medium_image_post(self):
        # ajuste ?p=<ID> para o ID do post com a imagem de 300kb
        self.client.get("/?p=3", name="post_medium_image")

    @task(3)
    def fetch_image(self):
        self.client.get("/wp-content/uploads/2025/10/medium-image.jpg", name="medium_image")
