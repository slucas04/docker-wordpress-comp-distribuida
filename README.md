# Trabalho 2 — WordPress com múltiplas instâncias + Nginx (balanceador)

## Resumo

Este repositório contém a orquestração do ambiente solicitado: **1 container Nginx** (balanceador), **3 containers WordPress** (`wordpress1`, `wordpress2`, `wordpress3`) que compartilham o mesmo banco de dados **MySQL (db)** e o mesmo volume de aplicação, orquestrados via `docker-compose.yml`.

---

## Estrutura do `docker-compose.yml`

Serviços criados:

* `db` — `mysql:5.7` (volume `db_data` para persistência)
* `wordpress1` — `wordpress:5.4.2-php7.2-apache` (volume `wp_data` → `/var/www/html`)
* `wordpress2` — idem
* `wordpress3` — idem
* `nginx` — `nginx:1.19.0` (expõe `80:80`, monta `nginx.conf` e `wp_data` em `/usr/share/nginx/html`)

> O arquivo `docker-compose.yml` está no repositório. Ele cria a rede Docker onde os serviços se resolvem por nome (ex.: `db`), define volumes nomeados para persistência e configura o Nginx para atuar como proxy reverso.

---

## Como o WordPress encontra o MySQL?

No `docker-compose.yml` definimos variáveis de ambiente nos containers WordPress:

```
WORDPRESS_DB_HOST: db:3306
WORDPRESS_DB_USER: wp_user
WORDPRESS_DB_PASSWORD: wp_pass
WORDPRESS_DB_NAME: wordpress
```

O Docker Compose cria uma rede interna em que `db` resolve para o IP do container MySQL. Assim, o WordPress usa `db:3306` para se conectar ao MySQL. A chave `depends_on: - db` no compose ajuda a iniciar o MySQL antes dos WordPress, porém **não** garante que o MySQL esteja pronto para aceitar conexões (para isso usar `healthcheck`).

---

## Como o Nginx faz o balanceamento?

No `nginx.conf` definimos um `upstream` com as três instâncias do WordPress e usamos `proxy_pass` para encaminhar as requisições. Também adicionamos um header de resposta para identificação do upstream:

```
add_header X-Upstream $upstream_addr;
proxy_pass http://wordpress;
```

O header `X-Upstream` aparece nos *response headers* e serve para validar qual instância respondeu. A resposta é HTTP: contém headers (onde está `X-Upstream`) e o body (HTML) — ou seja, o navegador recebe tanto o header quanto a página HTML.

---

### [Evidência 1] Status dos containers (`docker ps`)

```
NAMES        STATUS          PORTS
nginx        Up 19 minutes   0.0.0.0:80->80/tcp, [::]:80->80/tcp
wordpress3   Up 19 minutes   80/tcp
wordpress2   Up 19 minutes   80/tcp
wordpress1   Up 19 minutes   80/tcp
db           Up 19 minutes   3306/tcp, 33060/tcp
```

**O que prova:** apenas o Nginx expõe porta ao host; as instâncias WordPress e o MySQL estão acessíveis internamente.

---

### [Evidência 2] IPs dos containers WordPress (texto)

```
172.19.0.3
172.19.0.4
172.19.0.5
```

**O que prova:** IPs internos das instâncias — usados para correlacionar o `X-Upstream`.

---

### [Evidência 3] Balanceamento — `X-Upstream` (texto)

Trecho obtido (20 requisições):

```
X-Upstream: 172.19.0.5:80
X-Upstream: 172.19.0.3:80
X-Upstream: 172.19.0.4:80
X-Upstream: 172.19.0.5:80
X-Upstream: 172.19.0.3:80
X-Upstream: 172.19.0.4:80
X-Upstream: 172.19.0.5:80
X-Upstream: 172.19.0.3:80
X-Upstream: 172.19.0.4:80
X-Upstream: 172.19.0.5:80
X-Upstream: 172.19.0.3:80
X-Upstream: 172.19.0.4:80
X-Upstream: 172.19.0.5:80
X-Upstream: 172.19.0.3:80
X-Upstream: 172.19.0.4:80
X-Upstream: 172.19.0.5:80
X-Upstream: 172.19.0.3:80
X-Upstream: 172.19.0.4:80
X-Upstream: 172.19.0.5:80
X-Upstream: 172.19.0.3:80
```

**O que prova:** requisições foram atendidas alternadamente pelas 3 instâncias — validação do balanceamento.

---

### [Evidência 4] Montagem do `/var/www/html` (JSON)

```json
[{"Type":"volume","Name":"wordpress-multi-nginx_wp_data","Source":"/var/lib/docker/volumes/wordpress-multi-nginx_wp_data/_data","Destination":"/var/www/html","Driver":"local","Mode":"rw","RW":true,"Propagation":""}]
```

**O que prova:** uso de *named volume* (`wp_data`) para compartilhar o conteúdo entre instâncias.

---

### [Evidência 5] Prova visual do post + imagem (screenshot)

<img width="741" height="569" alt="image" src="https://github.com/user-attachments/assets/db435cac-72f6-44ea-b74f-7ffc7b80fec3" />

**O que provar:** o post e a imagem criados no painel WP aparecem no site servido pelo Nginx (persistência e compartilhamento de uploads).

---

## Observações finais e recomendações rápidas

* `depends_on` garante ordem de inicialização, mas não readiness do DB — recomenda-se usar `healthcheck` no `db` para produção.
* Named volumes são mais práticos no Windows; para usar bind-mount (`./wp_shared`) sem problemas prefira rodar no WSL2.
* O `X-Upstream` é um *response header* HTTP; o HTML é o *body*. Inclua ambos (texto `upstreams.txt` + screenshot do site) caso o professor peça header e conteúdo.
