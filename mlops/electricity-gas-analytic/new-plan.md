# Project Modernization Plan: Phase 2

## 1. Objective

The goal of this phase is to refactor the application's frontend to precisely match the new visual samples provided. This involves a shift in the technology stack and a complete "re-skinning" of the UI to achieve a more polished, modern, and data-centric aesthetic.

## 2. Technology Stack Pivot

To achieve the desired look and feel, the current Material-UI implementation will be replaced. The new stack will be:

-   **UI Framework:** **Tailwind CSS** - A utility-first CSS framework for creating custom, high-fidelity designs.
-   **Icon Library:** **Lucide React** - For clean, lightweight, and consistent icons, as suggested in the reference materials.
-   **Charting Library:** **Chart.js** (`react-chartjs-2`) - This will be retained as it is versatile and can be styled to match the new design.
-   **Core Framework:** **React** - No changes to the core framework.

## 3. Implementation Steps

### 3.1. Setup and Configuration

1.  **Install New Dependencies:**
    -   `npm install tailwindcss postcss autoprefixer`
    -   `npm install lucide-react`
2.  **Configure Tailwind CSS:**
    -   Generate `tailwind.config.js` and `postcss.config.js` files.
    -   Configure the `tailwind.config.js` to scan the `src` directory for component files.
3.  **Update Global Styles:**
    -   Modify `src/index.css` to include Tailwind's base, components, and utilities layers.
4.  **Cleanup Old Dependencies:**
    -   `npm uninstall @mui/material @emotion/react @emotion/styled @mui/icons-material`

### 3.2. Component Refactoring

Each component will be rewritten to use Tailwind CSS utility classes for styling and `lucide-react` for icons.

-   **`App.js`:**
    -   The main layout will be refactored. The top `AppBar` and `Tabs` will be replaced with a new navigation structure that matches the samples (e.g., top navigation with icons and text).

-   **`DataOverview.js`:**
    -   Recreate the key metric cards using `div`s styled with Tailwind.
    -   Integrate `lucide-react` icons into the cards.
    -   If applicable, add the "Data Input" section with file upload styling.

-   **`ConsumptionTrends.js`:**
    -   The `Line` chart will be retained.
    -   The container `Card` will be replaced with a `div` styled with Tailwind (background, padding, shadow, border-radius).
    -   Chart colors and fonts will be updated to match the new theme.

-   **`CostAnalysis.js`:**
    -   Recreate the two-column layout for the Pie and Line charts.
    -   Re-style the "Savings Suggestions" cards at the bottom.

-   **`UsagePatterns.js`:**
    -   Recreate the multi-chart layout.
    -   **Implement a Radar Chart** using `react-chartjs-2` to match the sample image.

-   **`ProfessionalReport.js`:**
    -   Perform a detailed reconstruction of the report layout using Tailwind's typography and spacing utilities.
    -   Re-style the tables, lists, and summary cards to precisely match the design.

## 4. Expected Outcome

The final application will be a visually identical replica of the provided sample images, with a clean, modern UI, improved data visualizations, and a more professional overall presentation. The underlying data logic will remain the same, but the user-facing interface will be completely overhauled.
