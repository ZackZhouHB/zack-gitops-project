---
title: "Migrating Blog to Django Web App"
date: 2025-07-21T04:28:57Z
slug: migrating-blog-to-django-web-app
categories: ["DevOps"]
aliases: ["/post/141/"]
legacy_id: 141
---
I originally used Jekyll, a straightforward static site generator, to build my blog. It was easy to set up and ideal for managing content in Markdown. However, it had its limitations: serving only static content meant a lack of dynamic features and essential tools like a built-in database and user management. That's when I decided to migrate to Django. With its ability to handle dynamic content and a fully integrated database, it was the perfect solution and the clear choice for the future of my blog.

[![Screenshot of the old Jekyll blog](/images/byb1.png)](/images/byb1.png)

**1. Setting Up the Local Django Environment**

I decided to build a Docker image to set up a portable Python environment. By mounting the working directory to my local Git repository, I ensured consistency across platforms. Using VSCode's container integration, I could launch directly into the development environment, making the setup seamless.

[![VSCode showing the Docker container setup](/images/web3.png)](/images/web3.png)

**2. Creating the Django Application**

The next step was to build the Django application. This involved structuring the project, creating models for blog posts, setting up user management, and managing content with Django's powerful ORM. A key task was writing a script to convert my old Jekyll Markdown posts into the new Django database format.

[![Django admin panel screenshot](/images/web4.png)](/images/web4.png)

**3. Cloud Hosting, Domain, and SSL**

I purchased a domain through Cloudflare, configured the DNS, and implemented SSL. This finally got rid of the tedious process of manually renewing a free SSL certificate every three months.

**4. Upgrading Django to the Latest Version**

Looking at the gap between Django 2.1 and 5.2 felt like staring up at a mountain. I knew a direct jump was risky, so I opted for an incremental approach, hopping between Long-Term Support (LTS) versions to ensure a secure and manageable upgrade.

```bash
# Navigate to the project directory
root@zack:~# vim Dockerfile

# Update requirements in both Django project and Docker context
vim requirements.txt

# Example change for one of the upgrade steps
Django==2.2  # Changed from 2.1 to 2.2
django-crispy-forms==2.3 # Updated
crispy-bootstrap4==2024.1 # Updated
# ... and other dependencies

# Install the upgraded packages
pip install -U -r requirements.txt

# Run checks and the test suite to find regressions
python manage.py check
python manage.py test

# Verify the new Django version
python3 -m django --version
```

This path felt much more manageable: 2.1 → 2.2 → 3.2 → 4.2 → 5.2.

**5. Modernizing the Layout and Fixing Dependencies**

Upgrade runtime (Python) from 3.8 slim to 3.13 slim in docker base image to be compatitable with Django 4.0+- Using a dedicated `upgrade` branch, merge to editing branch only ensure success of each version upgrade- Adjusted and updated the CSS to create a more modern layout.
  - Fixed `TemplateDoesNotExist` error where upgraded dependencies needed to be explicitly registered in `INSTALLED\_APPS` in `settings.py`.
  - Resolved CSRF errors by adding trusted origins to `settings.py`, a requirement for Django 4+ to handle flexible production IPs.

---

**6. Updating CI/CD with GitHub Actions**

I updated the existing GitHub Actions workflow from the Jekyll project to automate the deployment process for the new Django app, fixed the CI/CD pipeline and aligned all environments, so can be confident that what tested locally is what is running on target EC2. This reproducibility is the ultimate goal of DevOps practices.

[![GitHub Actions workflow for Django deployment](/images/web5.png)](/images/web5.png)

**Before Django version upgrade and Layout Modernization**

[![Cloudflare DNS and SSL configuration](/images/byb2.png)](/images/byb2.png)

---

**A Look at the New Design after upgrade**

[![Screenshot of the new, modern layout](/images/web8.png)](/images/web8.png)

**Achievements and Reflections**

After days of focused work, I leaned back and looked at what I had built. Here is a summary of the final achievements:

- ✅ A blazing-fast app running on Django 5.2 and Python 3.13.
- ✅ A robust, automated CI/CD pipeline that ensure reproducibility.
- ✅ Consistent environments across local, testing, and production, eliminating deployment surprises.
- ✅ A fresh, modern CSS layout that makes the whole app feel new again.

**Conclusion**

Migrating from Jekyll to Django wasn’t just about solving a technical problem—it was a demonstration of best DevOps practices. The journey was insightful, and I enjoyed the debugging challenges. It reaffirmed the importance of using the right tools for the job.
