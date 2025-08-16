# Personal Bank Statement Analyzer

A client-side, privacy-focused web application to analyze, categorize, and visualize your personal bank statements.

**Tags:** React, Chart.js, Data Visualization, Client-Side, Financial Analysis, Portfolio Project

---

## Introduction & Project Background

This project was born from a simple question: "How can I quickly understand my financial habits from a bank statement without uploading my sensitive data to a third-party service?" The Personal Bank Statement Analyzer is the answer. It's a powerful, interactive dashboard that runs entirely in your browser. 

Your data never leaves your machine. 

You can upload a standard CSV file from your bank, and the application instantly provides a detailed breakdown of your income, expenses, and spending categories. It intelligently handles multiple uploads over time, consolidating data and de-duplicating transactions to build a clean, unified financial timeline. It's a tool designed for privacy, speed, and deep financial insight.

## Core Features

*   **100% Client-Side:** All parsing, analysis, and rendering happens in the browser. User data is never sent over the network, ensuring absolute privacy.
*   **Intelligent Data Consolidation:** Upload multiple CSV files from different time periods. The app automatically merges them, removes duplicate transactions, and presents a single, unified dataset.
*   **Interactive Dashboard:** All components are linked. Filtering by a date range instantly updates all metrics, charts, and tables.
*   **Automatic Transaction Categorization:** A rule-based engine automatically assigns categories like "Dining", "Groceries & Shopping", and "Bills & Utilities" to your transactions.
*   **Time-Based Filtering:** Easily analyze your finances over specific periods with an intuitive date filter ("All Time", "This Month", "Last Month").
*   **Monthly Forecast:** Get a projection of next month's income and expenses based on a historical average of the last three months.
*   **Modern, Responsive UI:** A clean, dashboard-style interface built with a modern design system.

## Tech Stack & Design Philosophy

This project was built with a carefully selected, modern frontend stack, prioritizing user experience, privacy, and maintainability.

*   **React:** Chosen for its component-based architecture, which is ideal for building a dynamic, single-page application (SPA). It allows for efficient state management and a declarative UI.

*   **PapaParse:** A powerful, in-browser CSV parsing library. It was selected to reliably handle the complexities of CSV files without needing a backend.

*   **Chart.js & react-chartjs-2:** Used for creating beautiful, responsive, and interactive charts. Its ease of use and excellent documentation made it a perfect fit for visualizing the expense distribution pie chart.

*   **date-fns:** A modern, modular, and lightweight library for date manipulation. It was crucial for reliably parsing dates from various formats and powering the time-based filtering logic.

*   **Client-Side First Architecture:** This was the most important design decision. By committing to a client-side-only architecture (no backend, no database), we guarantee user privacy. All data is processed and stored locally in the browser's `localStorage`.

*   **Modern CSS:** The UI was styled using modern CSS features, including CSS Variables for a themable color system, CSS Grid for robust layouts, and a "card" based design for a clean, modern aesthetic.

## The Development Journey

This project was built iteratively, with each phase adding a significant layer of functionality.

1.  **Phase 1: Foundation & Core Logic:** We began by setting up the React project and implementing the basic file upload and CSV parsing. The initial goal was simply to display the raw data in a table and calculate the three key metrics: Total Income, Total Expenses, and Net Savings.

2.  **Phase 2: Categorization & Visualization:** To add more insight, we built a rule-based categorization engine to automatically tag each transaction. This was immediately paired with a `Chart.js` pie chart to provide the first layer of powerful data visualization.

3.  **Phase 3: Time-Series Analysis (The "Major Upgrade"):** This was a pivotal refactoring. We integrated `date-fns` and re-architected the app to be date-aware. This phase introduced the intelligent data consolidation logic (merging and de-duplicating multiple file uploads) and the interactive time-range filter buttons.

4.  **Phase 4: Predictive Analytics:** With a robust, time-aware foundation, we added the forecasting feature. This logic calculates a monthly average based on the last three months of data to provide a reasonable projection for the upcoming month.

5.  **Phase 5: Internationalization & Polish:** We performed a full translation of the UI from Chinese to English. This involved refactoring hardcoded strings and implementing a CSS-based workaround to style the browser-native file upload button, ensuring a seamless user experience.

6.  **Phase 6: UI/UX Modernization:** The final step was a complete visual overhaul. We implemented a professional, modern dashboard design system from the ground up, focusing on a clean color palette, a card-based layout, iconography, and improved typography.

## How to Run Locally

1.  Clone the repository.
2.  Navigate to the project directory: `cd bank-analyzer-app`
3.  Install dependencies: `npm install`
4.  Start the development server: `npm start`
5.  Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

## Future Improvements

*   **User-Defined Categories:** Allow users to create, edit, and delete categorization rules via a settings interface.
*   **Export to PDF:** Add a feature to export the current dashboard view as a PDF report.
*   **Trend Charts:** Implement a line chart to visualize income vs. expense trends over time.