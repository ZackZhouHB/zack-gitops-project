---
title: "{{ replace .File.ContentBaseName "-" " " | title }}"
date: {{ .Date }}
draft: true
categories: ["General"]
---

Write the post here. Images go in `static/images/` and are referenced as `![alt](/images/name.png)`.
