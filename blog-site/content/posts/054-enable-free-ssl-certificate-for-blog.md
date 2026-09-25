---
title: "Enable Free SSL certificate for blog"
date: 2023-02-07T23:28:37Z
slug: enable-free-ssl-certificate-for-blog
categories: ["AWS"]
aliases: ["/post/54/"]
legacy_id: 54
---
An interviewer told me this blog is insecure!!

- Generate free SSL certificate from <https://zerossl.com/>
- Validate the Certificate with Private Key via <https://www.sslshopper.com/certificate-key-matcher.html>
- Upload 'certificate.crt' and 'private.key' to web server `/etc/nginx/ssl/`

- Setting up NGINX HTTPS Server by including the `ssl` parameter to the listen directive in the server block under 'http' in 'nginx.conf':

```text
http {
    server {
        listen 443 ssl;
        server_name zackdevops.online;

        ssl_certificate /etc/nginx/ssl/certificate.crt;
        ssl_certificate_key /etc/nginx/ssl/private.key;
    }
    ...
}
```

- Fix 2 errors:

```text
2023/02/07 10:29:33 [emerg] 73175#73175: "server" directive is not allowed here in /etc/nginx/nginx.conf:11

2023/02/07 10:30:25 [error] 73207#73207: *1 directory index of "/usr/share/nginx/html/" is forbidden,client: 163.53.144.82, server: zackdevops.online, request: "GET / HTTP/1.1", host: "zackdevops.online"
2023/02/07 10:30:36 [error] 73207#73207: *1 directory index of "/usr/share/nginx/html/" is forbidden, client: 163.53.144.82, server: zackdevops.online, request: "GET / HTTP/1.1", host: "zackdevops.online"
```

Bingo! <https://zackdevops.online> connection is secure!
