# Django Blog Platform

This is a full-featured and modern blog application built with Django. It serves as a personal portfolio and technical blog, showcasing a range of web development and cloud engineering projects. The platform is designed with a clean user interface and is fully containerized for easy deployment and development.

## Key Features

*   **Full User Authentication:** Complete user management system including registration, login, logout, and password reset functionality.
*   **User Profiles:** Each user has a profile with a custom profile picture and a dedicated page to display all their posts.
*   **CRUD Operations for Posts:** Authenticated users can create, read, update, and delete their own blog posts.
*   **Markdown Editor:** Posts are written in Markdown using `django-markdownx`, allowing for rich text formatting, code blocks, embedded images, and more.
*   **Modern Frontend:** The user interface is built with Bootstrap 5 and a custom stylesheet, providing a clean, responsive, and modern aesthetic.
*   **Infinite Scroll:** The homepage features an infinite scroll mechanism, which dynamically loads more posts as the user scrolls down, enhancing the browsing experience.
*   **Containerized Application:** The entire application is containerized using **Docker** and **Docker Compose**, ensuring a consistent and reproducible environment for both development and deployment.

## Tech Stack

*   **Backend:** Python, Django
*   **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
*   **Database:** SQLite (for simplicity in development)
*   **Key Django Packages:**
    *   `django-crispy-forms` & `crispy-bootstrap4` for elegant form rendering.
    *   `Pillow` for image processing (profile pictures).
    *   `django-markdownx` for a rich Markdown editing experience.
*   **Containerization:** Docker, Docker Compose

## Project Structure

```
/django_project
|-- blog/                  # Core blog application (models, views, templates for posts)
|-- users/                 # User management application (profiles, authentication)
|-- django_project/        # Main Django project settings and configuration
|-- media/                 # Directory for user-uploaded files (e.g., profile pictures)
|-- static/                # Static files (CSS, JS, images)
|-- Dockerfile             # Defines the Docker image for the application
|-- docker-compose.yml     # Orchestrates the application services for development
|-- manage.py              # Django's command-line utility
|-- requirements.txt       # Python dependencies
```

## Getting Started

Follow these instructions to set up and run the project on your local machine.

### Prerequisites

*   **Docker:** [Install Docker](https://docs.docker.com/get-docker/)
*   **Docker Compose:** [Install Docker Compose](https://docs.docker.com/compose/install/)

### Setup and Running

1.  **Clone the repository and navigate to the project directory:**
    ```bash
    git clone <repository-url>
    cd django_project/docker
    ```

2.  **Build and Run with Docker Compose:**
    From within the `django_project/docker` directory, run the following command:
    ```bash
    docker-compose up --build
    ```
    This command will build the Docker image based on the `Dockerfile` and start the Django development server. The `-d` flag can be added to run it in detached mode.

3.  **Access the Application:**
    Once the container is running, open your web browser and navigate to:
    ```
    http://localhost:8000
    ```

4.  **Apply Database Migrations (if needed):**
    If you are setting up the database for the first time or if there are new migrations, open a new terminal and run:
    ```bash
    docker-compose exec python-dev python manage.py migrate
    ```

5.  **Create a Superuser:**
    To access the Django admin panel and manage users and posts, create a superuser:
    ```bash
    docker-compose exec python-dev python manage.py createsuperuser
    ```
    Follow the prompts to create your admin account.

6.  **Access the Admin Panel:**
    You can now log in to the admin panel at `http://localhost:8000/admin` with your superuser credentials.

## Usage

*   **Register:** New users can register for an account, but this feature is currently disabled in the template for public viewing. You can enable it by modifying the registration link in the templates.
*   **Login:** Existing users can log in to create and manage their posts.
*   **Create a Post:** Once logged in, click on "New Post" to open the Markdown editor and create a new blog entry.
*   **Update Profile:** Navigate to the "Profile" page to update your username, email, and profile picture.
