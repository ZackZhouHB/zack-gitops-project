from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from .models import Post
from django.core.paginator import Paginator
from django.http import HttpResponse

#from .models import BlogPost  

def post_list(request):
     posts = BlogPost.objects.all()
     return render(request, 'blog/post_list.html', {'posts': posts})


def home(request):
    context = {
        'posts': Post.objects.all().order_by('-date_posted')
    }
    return render(request, 'blog/home.html', context)


class PostListView(ListView):
    model = Post
    template_name = 'blog/home.html'  # <app>/<model>_<viewtype>.html
    context_object_name = 'posts'
    ordering = ['-date_posted']
    paginate_by = 12  # Show 10 posts per page to display 3-4 posts on screen

def infinite_scroll_posts(request):
    page_number = request.GET.get("page")
    
    try:
        page_number = int(page_number)
    except (ValueError, TypeError):
        page_number = 1

    # The initial page has 12 posts. Subsequent pages have 5.
    # This calculates the correct offset.
    initial_posts = 12
    posts_per_page = 5
    
    # Calculate the offset based on the page number
    # For page 2, offset is 12. For page 3, offset is 12 + 5 = 17, and so on.
    if page_number <= 1:
        offset = 0
        limit = initial_posts
    else:
        offset = initial_posts + (page_number - 2) * posts_per_page
        limit = posts_per_page

    posts_list = Post.objects.all().order_by('-date_posted')[offset:offset+limit]

    if not posts_list:
        return HttpResponse('')  # Return empty response if no more posts

    return render(request, "blog/post_list_partial.html", {"posts": posts_list})


class UserPostListView(ListView):
    model = Post
    template_name = 'blog/user_posts.html'  # <app>/<model>_<viewtype>.html
    context_object_name = 'posts'
    paginate_by = 20

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs.get('username'))
        return Post.objects.filter(author=user).order_by('-date_posted')


class PostDetailView(DetailView):
    model = Post


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['title', 'content']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['title', 'content']

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/'

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})
