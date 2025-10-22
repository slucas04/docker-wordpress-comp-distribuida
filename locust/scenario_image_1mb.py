from locust import HttpUser, task, between

class WebsiteUser(HttpUser):
    wait_time = between(1, 3)

    @task(2)
    def view_home(self):
        self.client.get("/")

    @task(5)
    def view_large_image_post(self):
        # ajusta ?p=<ID> para o ID do post com a imagem de ~1MB
        self.client.get("/?p=1", name="post_large_image")

    @task(3)
    def fetch_image(self):
        # caminho direto da imagem (substituir se necessário)
        self.client.get("/wp-content/uploads/2025/10/large-image.jpg", name="large_image")
