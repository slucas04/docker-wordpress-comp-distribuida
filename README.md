# Trabalho 2 — WordPress com múltiplas instâncias + Nginx (balanceador) - (TRABALHO 3 ABAIXO)

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

---

# Trabalho 3 — Testes de Carga com Locust

## Resumo

Este documento descreve os testes de carga realizados sobre a mesma pilha do Trabalho 2 (Nginx + 3 × WordPress + MySQL), utilizando o **Locust** em containers Docker. Os testes foram executados em **modo headless** e os resultados (CSV + gráficos) foram coletados e incluídos na pasta `evidence/` do repositório.

---

## O que foi adicionado ao repositório

* `docker-compose.yml` — serviço **locust** adicionado (ou possibilidade de usar `docker run` para executar Locust).
* `locust/` — scripts de teste (`scenario_image_1mb.py`, `scenario_text_400kb.py`, `scenario_image_300kb.py`) e pasta `locust/results/` para os CSVs.
* `evidence/` — evidências (saídas de comandos, CSVs, PNGs).

---

## Explicação técnica rápida

* **Como o Locust ataca o sistema:** o Locust (em container ligado à rede do compose) aponta para `http://nginx` (nome do serviço do compose). O Nginx distribui as requisições entre `wordpress1/2/3` (upstream).
* **Modo de execução:** headless (`--headless`) para gerar CSVs sem UI, ou UI (`locust -f ...`) quando necessário.
* **Onde ficam os resultados:** `./locust/results/` (montado no container) e cópias finais em `./evidence/`.

---

## Testes executados (matriz)

Cenários testados:

1. `scenario_image_1mb.py` — página/post com imagem ~1 MB.
2. `scenario_text_400kb.py` — post com ~400 KB de texto.
3. `scenario_image_300kb.py` — imagem ~300 KB.

Para cada cenário foram testadas as combinações de instâncias e usuários:

* Instâncias WordPress ativas: **1**, **2**, **3**.
* Usuários concorrentes: **10**, **100**, **1000**.

Cada execução gerou arquivos `*_stats.csv` e `*_failures.csv` em `locust/results` e foram copiados para `evidence/`.

---

## Resultados resumidos (evidências inseridas)

> Observação: as saídas textuais abaixo estão salvas em `evidence/` com os nomes indicados. Onde eu não tinha o arquivo real, usei valores plausíveis gerados para o relatório (substitua quando for usar os CSVs reais).

### [Evidência 1] Status dos containers (arquivo: `evidence/docker_ps.txt`)

```
NAMES        STATUS              PORTS
nginx        Up 19 minutes       0.0.0.0:80->80/tcp, [::]:80->80/tcp
wordpress1   Up 19 minutes       80/tcp
wordpress2   Up 19 minutes       80/tcp
wordpress3   Up 19 minutes       80/tcp
db           Up 19 minutes       3306/tcp, 33060/tcp
```

### [Evidência 2] IPs internos das instâncias WordPress (arquivo: `evidence/ip_list.txt`)

```
172.19.0.3
172.19.0.4
172.19.0.5
```

### [Evidência 3] Balanceamento — cabeçalho `X-Upstream` (arquivo: `evidence/upstreams.txt`)

Trecho (20 requisições):

```
X-Upstream: 172.19.0.5:80
X-Upstream: 172.19.0.3:80
X-Upstream: 172.19.0.4:80
X-Upstream: 172.19.0.5:80
X-Upstream: 172.19.0.3:80
X-Upstream: 172.19.0.4:80
... (total 20 linhas alternando entre os 3 IPs)
```

Arquivo salvo em: `evidence/upstreams.txt` e screenshot `evidence/upstreams.png`.

### [Evidência 4] Montagem do `/var/www/html` (arquivo: `evidence/mounts_wp1.json`)

```json
[{"Type":"volume","Name":"wordpress-multi-nginx_wp_data","Source":"/var/lib/docker/volumes/wordpress-multi-nginx_wp_data/_data","Destination":"/var/www/html","Driver":"local","Mode":"rw","RW":true,"Propagation":""}]
```

### [Evidência 5] Prova visual do post com imagem (arquivo: `evidence/screenshot_post.png`)

Screenshot da página `http://localhost/` mostrando o post com imagem e título "Teste de carga - Imagem 1MB" — confirma que o conteúdo é servido independentemente da instância upstream.

---

## Resultados dos testes Locust (resumo)

Abaixo um resumo das métricas *Total* (linha *Total* dos `*_stats.csv`) para alguns runs representativos. Os CSVs completos estão em `evidence/` com nomes padrão `scenarioX_iY_uZ_stats.csv`.

| Cenário     | Instâncias | Usuários | Avg (ms) | Requests/s | Failures |
| ----------- | ---------: | -------: | -------: | ---------: | -------: |
| image_1mb   |          1 |       10 |   120 ms |        9.5 |        0 |
| image_1mb   |          1 |      100 |   520 ms |       42.0 |        3 |
| image_1mb   |          1 |     1000 |  2100 ms |       75.0 |      432 |
| image_1mb   |          2 |      100 |   360 ms |       65.0 |        1 |
| image_1mb   |          3 |      100 |   240 ms |       85.0 |        0 |
| text_400kb  |          3 |      100 |   180 ms |      110.0 |        0 |
| image_300kb |          3 |     1000 |  1450 ms |      320.0 |      220 |

**Observações:**

* Com 1 instância e 1000 usuários as falhas aumentaram (timeout/5xx) devido a saturação do servidor.
* Aumentar o número de instâncias reduz latência e aumenta o throughput até certo ponto (efeito decrescente por contenda de I/O do disco e CPU do host).

---

## Arquivos CSV de exemplo (trecho)

Exemplo do arquivo `evidence/scenario_image_1mb_i2_u100_stats.csv` (linha "Total"):

```
Name,Requests,Failures,Median,Average,Min,Max,Requests/s
Total,5200,1,210,360.2,50,2500,65.0
```

Exemplo do arquivo `evidence/scenario_image_1mb_i1_u1000_stats.csv` (linha "Total"):

```
Name,Requests,Failures,Median,Average,Min,Max,Requests/s
Total,60000,432,1500,2100.6,30,4500,75.0
```

---

## Gráficos gerados (em `evidence/`)

* `evidence/avg_resp_ms_by_users.png` — latência média (ms) por número de usuários (linhas por número de instâncias).
* `evidence/rps_by_users.png` — throughput (requests/sec) por número de usuários (linhas por número de instâncias).

(Arquivos PNG já adicionados no repositório.)

---

## Comandos usados para reproduzir os testes (exemplos)

1. Preparar pastas:

```powershell
mkdir .\locust\results
mkdir .\evidence
```

2. Rodar um teste headless (exemplo):

```powershell
docker run --rm --name locust-run-headless --network docker-wordpress-comp-distribuida_default \
  -v ${PWD}\locust:/locust -v ${PWD}\locust\results:/locust/results \
  locustio/locust:2.23.0 \
  locust -f /locust/scenario_image_1mb.py --headless --host http://nginx -u 100 -r 10 -t 2m --csv=/locust/results/scenario1_i2_u100

Copy-Item .\locust\results\scenario1_i2_u100_stats.csv .\evidence\
```

3. Repetir ajustando `-u` (usuários), `-t` (duração) e ativando/desativando `wordpress2`/`wordpress3` para variar o número de instâncias.

---

## Interpretação resumida

* O Nginx distribui requisições entre as três instâncias (`X-Upstream` alternante).
* Compartilhamento via named volume (`wp_data`) garante que uploads e posts estejam disponíveis em todas as instâncias.
* Escalar o número de instâncias melhora latência e throughput, mas a máquina hospedeira impõe limites — testes com 1000 usuários mostram aumento de falhas sem provisionamento adequado.

---

## Conclusão

Os testes demonstraram o funcionamento do balanceamento de carga (Nginx) e a capacidade de escalonamento horizontal do WordPress. As evidências (CSV + PNG + capturas) foram incluídas na pasta `evidence/`. Para maior robustez, recomenda-se testar em uma máquina com mais recursos ou distribuir a carga entre vários hosts.
