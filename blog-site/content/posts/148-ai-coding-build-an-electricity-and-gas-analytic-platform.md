---
title: "AI Coding - Build an Electricity and Gas Analytic Platform"
date: 2025-08-14T07:45:20Z
slug: ai-coding-build-an-electricity-and-gas-analytic-platform
categories: ["Machine Learning"]
aliases: ["/post/148/"]
legacy_id: 148
---
In the past few days, I got an idea from my recent electricity and gas bills—thinking about how to run data analysis to examine usage patterns and trends using the Python approach: employing Pandas for reading data, using Numpy for normalisation, and Matplotlib to create a few visualisations.

However, this time I wanted to try talking to Gemini CLI via the terminal to see if it could generate a web-based analytical platform for me, as someone with no developer background.

**Objective: Zack's Super Cool Electricity and Gas Consumption Analysis Platform**

Initially, I got two datasets in CSV format based on energy consumption, which contained electricity and gas hourly usage data for the recent 2 months. I told Gemini CLI via the terminal.

[![[Image Placeholder 01: Introduction Graphic]](/images/ai0.png)](/images/ai0.png)

```text
Please check my power and gas usage from @electricity_consumption_2months_patterned.csv and @gas_consumption_2months_patterned.csv, acting like a real professional analysis to see the usage pattern and trends insight
```

It understood my request, created a requirement document, chose the tech stack and framework, created scripts to perform the required data analyses, and then built the web app to enable uploading CSVs to analyse trends, with insights into peak usage periods, and to predict future consumption patterns.

```bash
Please generate a professional requirements and design doc, as I need a web platform to allow users to upload such usage CSV to have power and gas usage and trends analysed

# Project: Energy Consumption Analysis and Visualization

## 1. Overview

The goal of this project is to analyze hourly electricity and gas consumption data from CSV files to understand usage patterns, identify trends, and visualize the findings in a web-based format. The system will also provide a professional report with optimization suggestions and allow for data export.

## 2. Data Input

The system will accept two CSV files as input:

- `electricity_consumption_2months_patterned.csv`: Containing electricity usage data.
- `gas_consumption_2months_patterned.csv`: Containing gas usage data.

### Data Format

Each CSV file is expected to have the following columns:

- `Consumption (kwh)`: Energy consumption in kilowatt-hours.
- `Estimated Cost Inc. Tax (p)`: Estimated cost in pence.
- `Start`: The start time of the consumption period.
- `End`: The end time of the consumption period.

## 3. Data Processing and Analysis

The backend of the application will perform the following steps:

1.  **Data Loading:** Load the electricity and gas consumption data from the provided CSV files.
2.  **Data Cleaning and Preparation:**
    - Parse the `Start` and `End` columns into datetime objects.
    - Handle any missing or erroneous data.
    - Create new features from the timestamps, such as:
        - Hour of the day
        - Day of the week
        - Week of the year
        - Month
3.  **Data Analysis:**
    - **Aggregate Data:** Calculate daily, weekly, and monthly consumption and cost for both electricity and gas.
    - **Trend Analysis:** Analyze the consumption and cost trends over time.
    - **Peak/Valley Usage Analysis:** Determine the times of day and days of the week with the highest and lowest energy consumption.
    - **Cost Analysis:**
        - **Cost Composition:** Analyze the proportion of electricity and gas costs.
        - **Cost Comparison:** Compare costs across different time periods.
        - **Savings Potential Assessment:** Evaluate potential savings based on usage patterns.
    - **Usage Pattern Analysis:**
        - **Usage Habit Analysis:** Identify and analyze the user's energy consumption habits.
        - **Anomaly Detection:** Detect and flag any unusual consumption data points.
        - **Pattern Recognition:** Recognize and highlight recurring consumption patterns.

## 4. Visualization and Reporting

The web interface will be divided into the following pages:

### 4.1. Data Overview Page

-   **Key Metrics:** Display key indicators such as total consumption, total cost, and average consumption.
-   **Overall Statistics:** Provide a summary of the data.

### 4.2. Consumption Trend Analysis Page

-   **Time Series Chart:** Interactive line chart for visualizing hourly consumption data.
-   **Trend Charts:** Bar charts for daily, weekly, and monthly consumption and cost trends.
-   **Peak/Valley Analysis:** Visualizations to highlight peak and off-peak usage.

### 4.3. Cost Analysis Page

-   **Cost Composition Chart:** Pie or donut chart showing the breakdown of costs between electricity and gas.
-   **Cost Comparison View:** A view to compare costs over different periods.
-   **Savings Potential:** Display potential savings with actionable insights.

### 4.4. Usage Pattern Analysis Page

-   **Habit Analysis:** Visualizations to show consumption habits (e.g., heatmap of hourly usage).
-   **Anomaly Highlighting:** Highlight anomalies directly on the time series charts.
-   **Pattern Display:** Show identified recurring patterns.

### 4.5. Professional Report Page

-   **Comprehensive Report:** A downloadable summary report of the analysis.
-   **Optimization Suggestions:** Provide a list of recommendations for reducing consumption and costs.
-   **Data Export:** Buttons to export the raw and processed data to CSV.

## 5. Technology Stack

-   **Backend:** Python with Flask or FastAPI.
-   **Data Analysis:** Pandas.
-   **Frontend:** React or Vue.js.
-   **Charting Library:** Chart.js or D3.js.
-   **Styling:** Bootstrap or Tailwind CSS.

## 6. Deployment and Execution

The application will be designed to run locally. The user will be able to:

1.  Place the consumption CSV files in a designated `data` directory.
2.  Run a single command to start the web server.
3.  Access the visualizations and reports through a web browser.
```

Following the design above, it took about 30 minutes with 3 rounds of debugging to fix issues like the time attribute in the dataset and some npm package import issues. The web page looked pretty nice and modern:

[![[Image Placeholder 01: Introduction Graphic]](/images/ai1.png)](/images/ai1.png)

[![[Image Placeholder 02: Introduction Graphic]](/images/ai2.png)](/images/ai2.png)

When looking at weekly trends, the AI models highlight interesting patterns, such as peak energy usage at different times during the day and over the week, which correlates with more time spent at home. This level of insight was once reserved for professional analysts but is now accessible to anyone with the right dataset.

[![[Image Placeholder 03: Introduction Graphic]](/images/ai3.png)](/images/ai3.png)

[![[Image Placeholder 04: Introduction Graphic]](/images/ai4.png)](/images/ai4.png)

[![[Image Placeholder 05: Introduction Graphic]](/images/ai5.png)](/images/ai5.png)

Even with a professional summary report.

[![[Image Placeholder 06: Introduction Graphic]](/images/ai6.png)](/images/ai6.png)

**The Transformation of Programming**

My typical approach involves using Python as my preferred and familiar toolset for one-off analyses. However, this AI experiment helped me build a reusable React application where data could be easily uploaded and re-analysed. It chose a stack of technical frameworks that I haven’t mastered, completing in 30 minutes what would have taken me days manually.

This level of efficiency is both unsettling and strangely reassuring. If AI can compress days of work into minutes, what is our true value? In the future, the key to competition may no longer lie in mastering every framework, but in the vision we apply to them.

**Conclusion: A Future Built with AI**

Claude Code or Gemini CLI won’t replace most programmers, but they will empower those who master them to become far more effective. The real change isn’t just technical; it’s a fundamental shift in our roles.

In the past, developers’ value was in translating requirements into code. Now, it lies in proposing good ideas and solving real-world problems. Code is just a tool, and AI helps us wield it. AI can execute the plan, but we must provide the vision.

This is why labels like "Python programmer" or "front-end engineer" are becoming obsolete. The only title that matters now is "problem-solver using AI." The greatest threat isn’t that AI will take your job, but that refusing to embrace it will make your skills irrelevant.

The full source code and dataset are now available at [my GitHub repo](https://github.com/ZackZhouHB/zack-gitops-project/tree/editing/mlops/electricity-gas-analytic).
