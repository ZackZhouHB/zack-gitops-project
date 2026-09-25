---
title: "AI-assisted Coding with Google Gemini Cli"
date: 2025-07-22T14:08:01Z
slug: ai-assisted-coding-with-google-gemini-cli
categories: ["DevOps"]
aliases: ["/post/143/"]
legacy_id: 143
---
In the last post, I used Claude Code with Kimi K2 to complete the Django web app layout optimization. One thing I wasn’t satisfied with was the pagination system on this Django blog. It used a numbered pagination interface at the bottom of the home page—functional, but a bit dated. I wanted to modernize it with automatic loading of more posts via infinite scroll.

[![[Image Placeholder 01: Introduction Graphic]](/images/gemini6.png)](/images/gemini6.png)

However, I couldn’t get this done using Kimi K2. Despite spending a significant number of tokens (and money), the model couldn’t provide a working solution.

So, I decided to try Google Gemini CLI to see how it would handle the task.

**Objective: Add Infinite Scroll**

The goal was simple: show the initial 12 posts, but instead of making users click “Next” or choose a page number, automatically load 5 more posts as they scroll towards the bottom of the page.

**Getting Started: Installing Gemini CLI**

Ensure Node.js v18 or higher is installed, and install Google Gemini CLI globally:

```bash
# Install curl, Node.js & npm (v20.x)
RUN apt-get update \
 && apt-get install -y curl ca-certificates \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y nodejs \
 && rm -rf /var/lib/apt/lists/*

# Install Google Gemini CLI globally (non-interactive)
RUN npm install -g @google/gemini-cli
```

**Launching Gemini and Authenticating**

Run `gemini` in terminal and follow the OAuth flow to log in with Google account. This unlocks free access to Gemini 2.5 Pro.

[![Initializing Gemini CLI in the terminal.](/images/gemini2.png)](/images/gemini2.png)

[![Google OAuth screen for Gemini CLI authentication.](/images/gemini4.png)](/images/gemini4.png)
[![Gemini CLI successfully authenticated and ready for use.](/images/gemini3.png)](/images/gemini3.png)

**Describing the Goal to Gemini CLI**

Talk to Gemini in plain English:

*“Can you validate the Django web app I'm running in the current folder? I think on the home page it lists 12 posts by default, sorted from newest. There are pagination buttons at the bottom to navigate to older posts. I don't want users to click pagination buttons anymore. Instead, can Django automatically show 12 posts by default, then load 5 more as the user scrolls down? Is that achievable?”*

Gemini immediately understood. It read the local Django files and settings, identified the feature as infinite scroll and laid out a clear plan:

- **Backend (Django):** Keep existing paginator logic but add a new view to handle asynchronous requests. This view will return a small HTML snippet with the next batch of posts.
- **Frontend (JavaScript):** Modify home.html to detect when users scroll to the bottom. Then use fetch() to request new posts and append them to the DOM. Remove old pagination.

```text
✔ ReadManyFiles will attempt to read and concatenate files using patterns: `blog/views.py`, `blog/templates/blog/home.html` (within target…)

### ReadManyFiles Result (Target Dir: `/mnt/f/zack-gitops-project/django_project`)

Successfully read and concatenated content from **2 file(s)**.

**Processed Files:**
- `blog/templates/blog/home.html`
- `blog/views.py`
```

I gave `allow` so Gemini can now create and edit files under the Django folder for me.

**Step 1: Modifying the Backend**

**Creating the New View**

Gemini added a new view in `blog/views.py` to serve the extra posts:

```python
# blog/views.py

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render
from .models import Post

def infinite_scroll_posts(request):
    page_number = request.GET.get("page")
    posts_list = Post.objects.all().order_by('-date_posted')
    paginator = Paginator(posts_list, 5)
    page_obj = paginator.get_page(page_number)
    return render(request, "blog/post_list_partial.html", {"posts": page_obj})
```

**Creating the Partial Template**

This template (`post_list_partial.html`) includes only the post loop, making the response lightweight:

```text
<!-- blog/templates/blog/post_list_partial.html -->

{% for post in posts %}
  <article class="media content-section">
    <img class="rounded-circle article-img" src="{{ post.author.profile.image.url }}">
    <div class="media-body">
      <div class="article-metadata">
        <a class="mr-2" href="{% url 'user-posts' post.author.username %}">{{ post.author }}</a>
        <small class="text-muted">{{ post.date_posted|date:"F d, Y" }}</small>
      </div>
      <h2><a class="article-title" href="{% url 'post-detail' post.id %}">{{ post.title }}</a></h2>
      <p class="article-content">{{ post.content|striptags|slice:":200" }}</p>
      <a href="{% url 'post-detail' post.id %}" class="read-more-link">Read more</a>
    </div>
  </article>
{% endfor %}
```

**Adding the URL**

Gemini updated `blog/urls.py`:

```bash
# blog/urls.py

urlpatterns = [
    # ... other paths
    path("infinite-scroll-posts/", views.infinite_scroll_posts, name="infinite-scroll-posts"),
]
```

**Step 2: Updating the Frontend**

Gemini then modified `home.html` to remove the pagination and include infinite scroll logic:

```text
<!-- blog/templates/blog/home.html -->

{% extends "blog/base.html" %}
{% block content %}
  <div id="post-container">
    {% for post in posts %}
      <article class="media content-section">
        <!-- ... post content ... -->
      </article>
    {% endfor %}
  </div>

  <div id="loading" style="display:none;">
    <p>Loading...</p>
  </div>

  <script>
    let page = 2;
    let isLoading = false;
    const loading = document.getElementById('loading');
    const postContainer = document.getElementById('post-container');

    function loadMorePosts() {
      if (isLoading) return;
      isLoading = true;
      loading.style.display = 'block';

      fetch(`/infinite-scroll-posts/?page=${page}`)
        .then(response => response.text())
        .then(data => {
          if (data.trim().length > 0) {
            postContainer.innerHTML += data;
            page++;
            isLoading = false;
            loading.style.display = 'none';
          } else {
            loading.style.display = 'none';
            window.removeEventListener('scroll', handleScroll);
          }
        })
        .catch(error => {
          console.error('Error loading more posts:', error);
          isLoading = false;
          loading.style.display = 'none';
        });
    }

    function handleScroll() {
      if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 200) {
        loadMorePosts();
      }
    }

    window.addEventListener('scroll', handleScroll);
  </script>
{% endblock content %}
```

**Conclusion**

And just like that, the feature was complete. Now, the home page loads 12 posts initially, and as I scroll, new posts appear automatically.

This was an exciting example of AI-assisted programming and development. Gemini CLI didn’t just generate code—it understood the requirement, outlined a clear plan, and executed it smoothly by accessing local file system and manage everything for me.

It’s like having a senior full-stack developer knowing every type of programming language or application on standby—someone who understands your ideas in plain language and coding them to life. This is truely a game-changer for people without a programming background, being able to optimize a Django web app—handling backend views, URL routing, and frontend JavaScript—feels wild.

We’re truly in the AI era. Every day there are new or enhanced AI model launching, they chasing to be the top. Imagine two years ago, how people were excited by the first version of ChatGPT. Now crazy in AI coding race: Claude Code, Gemini, GPT-4o, Kimi K2, Qwen Code, and others
