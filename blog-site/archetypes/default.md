---
title: "{{ replace .File.ContentBaseName "-" " " | title }}"
slug: "{{ .File.ContentBaseName }}"
date: {{ .Date }}
draft: false
categories: ["General"]
---

Put images in this post's folder (next to this index.md) and reference them by file name:

![Architecture diagram](diagram.png)
