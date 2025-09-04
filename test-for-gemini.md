run-gemini-cli is a GitHub Action that integrates Gemini into your development workflow via the Gemini CLI. It acts both as an autonomous agent for critical routine coding tasks, and an on-demand collaborator you can quickly delegate work to.

Use it to perform GitHub pull request reviews, triage issues, perform code analysis and modification, and more using Gemini conversationally (e.g., @gemini-cli fix this issue) directly inside your GitHub repositories.


Quick Start
1. Get a Gemini API Key
2. Add it as a GitHub Secret
3. Update your .gitignore
4. Choose a Workflow
5. Try it out!

Workflows
Gemini Dispatch
Issue Triage
Pull Request Review
Gemini CLI Assistant


Features
Automation: Trigger workflows based on events (e.g. issue opening) or schedules (e.g. nightly).
On-demand Collaboration: Trigger workflows in issue and pull request comments by mentioning the Gemini CLI (e.g., @gemini-cli /review).
Extensible with Tools: Leverage Gemini models' tool-calling capabilities to interact with other CLIs like the GitHub CLI (gh).
Customizable: Use a GEMINI.md file in your repository to provide project-specific instructions and context to Gemini CLI.

Quick Start
Get started with Gemini CLI in your repository in just a few minutes:

1. Get a Gemini API Key
Obtain your API key from Google AI Studio with generous free-of-charge quotas

2. Add it as a GitHub Secret
Store your API key as a secret named GEMINI_API_KEY in your repository:

Go to your repository's Settings > Secrets and variables > Actions
Click New repository secret
Name: GEMINI_API_KEY, Value: your API key

3. Update your .gitignore
Add the following entries to your .gitignore file:

# gemini-cli settings
.gemini/

# GitHub App credentials
gha-creds-*.json

4. get and test Workflow
You have two options to set up a workflow:

Start the Gemini CLI in your terminal under local repo folder, In Gemini CLI in your terminal, type:

/setup-github

5. Try it out!
Pull Request Review:

Here I created a test branch, made change to create a new markdown file, then create a pull request in your repository and request gemini to run and trigger automatic review by Comment @gemini-cli /review on an existing pull request to manually trigger a review

@gemini-cli Please explain what the test-for-gemini.md file does.

Workflows
This action provides several pre-built workflows for different use cases. Each workflow is designed to be copied into your repository's .github/workflows directory and customized as needed.

Gemini Dispatch
This workflow acts as a central dispatcher for Gemini CLI, routing requests to the appropriate workflow based on the triggering event and the command provided in the comment. For a detailed guide on how to set up the dispatch workflow, go to the Gemini Dispatch workflow documentation.

Issue Triage
This action can be used to triage GitHub Issues automatically or on a schedule. For a detailed guide on how to set up the issue triage system, go to the GitHub Issue Triage workflow documentation.

Pull Request Review
This action can be used to automatically review pull requests when they are opened. For a detailed guide on how to set up the pull request review system, go to the GitHub PR Review workflow documentation.

Gemini CLI Assistant
This type of action can be used to invoke a general-purpose, conversational Gemini AI assistant within the pull requests and issues to perform a wide range of tasks. For a detailed guide on how to set up the general-purpose Gemini CLI workflow, go to the Gemini Assistant workflow documentation.

you see when I update the commant in PR conversation, it triggered the action workflow, first with Dispatch yml, then it detected my request and choose the review yml, then offer me recommendation and put in the PR conversation

Cloclusion

This run-gemini-cli github action workflow doesn’t replace human review, but it’s like having a tireless reviewer that handles boring checks and gives immediate explanations. Humans can then focus on design, architecture, and business logic.

How this improves over manual PR review

Automated triage & context check

Gemini can catch low-level issues (missing newlines, lint problems, style, docs) without needing a human to even look.

That saves reviewers from wasting mental effort on trivial formatting/style details.

On-demand explanations

You (or any collaborator) can type @gemini-cli Please explain… to get contextual explanations of files, changes, or why a modification matters.

In manual reviews, you’d need to ask the author and wait — now you get it instantly.

Faster feedback loop

Gemini reviews as soon as a PR is opened (thanks to pull_request.opened event).

Humans don’t always review immediately — Gemini ensures every PR gets some feedback right away.

Standardized review quality

Humans vary in thoroughness. Gemini enforces a baseline (e.g., documentation check, structure, formatting).

This ensures consistent standards across the repo.

Reduces reviewer fatigue

Developers can focus on high-level design/logic decisions, while Gemini handles repetitive, mechanical checks.

That makes human review time more valuable.

Traceable & reproducible

Every Gemini action run is logged under GitHub Actions.

That means you can always inspect how/why it made a comment — unlike a human’s “gut feel.”

🚀 Possible Improvements for This Workflow

Looking at the YAML you pasted, a few enhancements could make it even stronger:

Run static analysis automatically
Add jobs to run eslint, flake8, pylint, or prettier depending on project type, so Gemini’s review can include real lint results.

Auto-fix trivial issues
Instead of only commenting “missing newline”, Gemini could push a patch commit with that newline (with approval from repo settings).

Configurable prompts
Add a repo-level config (e.g., .gemini.yml) that specifies what Gemini should always check (docs coverage, test presence, changelog update, etc.).

Require Gemini review before merge
Protect branches so PRs need at least one “reviewed by gemini-cli” check before merge. Ensures baseline automated QA.

Smarter comment parsing
Right now it looks for @gemini-cli at the start of a comment. You could extend this so people can just mention anywhere in the body.