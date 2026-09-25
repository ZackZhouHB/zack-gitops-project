---
title: "Automate PR Review using Gemini CLI within GitHub Action"
date: 2025-09-03T12:29:23Z
slug: automate-pr-review-using-gemini-cli-within-github-action
categories: ["DevOps"]
aliases: ["/post/149/"]
legacy_id: 149
---
I recently found an interesting tool **run-gemini-cli**, a GitHub Action that integrates Gemini directly into your repositories. I was intrigued by its promise to perform pull request reviews, triage issues, and even modify code using conversational commands right inside GitHub action workflow. Let's try it out.

My goal was to see if I could use this action to get instant, automated feedback on pull requests. Instead of waiting for a human to spot simple issues, I wanted an AI to do the first pass, check for common problems, and even explain code changes on demand.

**Quick Start: Getting it Running**

**1. Get a Gemini API Key**
First, This one needs an API key. I grabbed one from Google AI Studio, which has a pretty generous free tier.

[![[Image Placeholder 01: Introduction Graphic for Gemini GitHub Action]](/images/action1.png)](/images/action1.png)

**2. Add it as a GitHub Secret**
Next, we need to save the API key in git repository's secrets (under `Settings > Secrets and variables > Actions`). Just go and create a new secret named `GEMINI_API_KEY` and pasted API key there.

[![[Image Placeholder 01: Introduction Graphic for Gemini GitHub Action]](/images/action2.png)](/images/action2.png)

**3. Update the .gitignore**
The CLI creates a local settings folder and temporary credentials, so I added them to my `.gitignore` file to keep the repo clean.

```text
gemini-cli settings
.gemini/

GitHub App credentials
gha-creds-*.json
```

**4. Set up the Workflow**
This was the fun part. Gemini official Git repo provided a list of example action workflows, which can be copied directly into my local repo .workflow folder with a simple command in GEMINI Cli:

```text
/setup-github
```

This automatically pulled the example workflow YAML files in my `.github/workflows` directory.

[![[Image Placeholder 01: Introduction Graphic for Gemini GitHub Action]](/images/action3.png)](/images/action3.png)

[![[Image Placeholder 01: Introduction Graphic for Gemini GitHub Action]](/images/action4.png)](/images/action4.png)

**5. Try it out!**
Now everything is set up, it's time for a test drive. Let's create a testing branch, add a test markdown file, and open a pull request. To trigger the review, I need to leave a comment and @gemini-cli in the PR description:

```text
@gemini-cli Please explain what the test-for-gemini.md file does.
```

As soon as I posted the comment, it automatically triggered a Gemini GitHub Action. The `Gemini Dispatch` workflow correctly identified my request in the comment and triggered the `review` workflow later.

You see it installed Gemini Cli in a runner, using both GitHub key and the Gemini API key, to run an AI-based PR review based on what I said in the comment. It analysed the new markdown file I created in the test branch, provided a recommendation in the workflow output, and put its opinion right in the PR conversation with suggested change reflected in the PR ready to update and merge.

[![[Image Placeholder 02: Gemini CLI's review comment in a GitHub pull request]](/images/action5.png)](/images/action5.png)

[![[Image Placeholder 02: Gemini CLI's review comment in a GitHub pull request]](/images/action6.png)](/images/action6.png)

[![[Image Placeholder 02: Gemini CLI's review comment in a GitHub pull request]](/images/action7.png)](/images/action7.png)

[![[Image Placeholder 02: Gemini CLI's review comment in a GitHub pull request]](/images/action8.png)](/images/action8.png)

**Other exampe Gemini Workflows**

The action comes with several pre-built workflows that can be useful:

- **Gemini Dispatch:** This acts as the central router. It listens for comments and triggers the right workflow, whether it's for reviewing a PR or triaging an issue.
- **Issue Triage:** This can automatically label, comment on, and manage new GitHub Issues. I can see this being a huge time-saver for open-source projects.
- **Pull Request Review:** This is the one I used. It automatically reviews PRs when they're opened or when you manually trigger it with a comment.
- **Gemini CLI Assistant:** This gives you a general-purpose, conversational AI assistant right in your PRs and issues for a whole range of tasks.

**Final Thoughts & What's Next**

My key takeaway is that the `run-gemini-cli` action is a fantastic AI collaborator. It doesn’t replace human review, but it excels at being a tireless assistant that handles the repetitive first-pass checks, provides instant context on demand, and enforces a consistent quality bar on every pull request.

This immediately speeds up the feedback loop and frees up our team to focus on what really matters—architecture, logic, and design—instead of getting bogged down in minor details. It's a powerful foundation, and I'm already thinking about ways to push it further, like letting it auto-fix trivial errors or integrating it more deeply with other static analysis tools.

Explore more fun, features or examples from its official [GitHub repo](https://github.com/google-github-actions/run-gemini-cli)
