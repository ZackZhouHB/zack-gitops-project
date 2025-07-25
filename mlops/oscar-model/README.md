# Oscar Best Picture Prediction

This project documents the process of building a machine learning model to predict the winner of the "Best Picture" award at the Academy Awards. The project evolves from a simple baseline model to a more sophisticated one, demonstrating the importance of data engineering, feature selection, and choosing the right modeling approach for an imbalanced dataset.

## Project Idea

The core idea is to leverage historical data to forecast future Oscar winners. Predicting awards is a classic classification problem, but it comes with a significant challenge: class imbalance. In any given year, there are many nominees but only one winner, making the "winner" class a rare event. This project tackles this challenge head-on.

We started with a basic approach and iteratively improved it:
1.  **Initial Work (`oscar111.ipynb`):** Data gathering, cleaning, and a baseline logistic regression model.
2.  **Enhancement (`oscar_lgbm_prediction.ipynb`):** Introduction of a more powerful LightGBM model, advanced feature engineering, and specific techniques to handle class imbalance, leading to successful predictions.

## Data Engineering

The foundation of this project is a robust dataset compiled from multiple sources.

### Phase 1: Data Collection and Enrichment (`oscar111.ipynb`)

1.  **Initial Dataset:** The project began with `the_oscar_award.csv`, containing historical Oscar nomination data.
2.  **Filtering:** The data was filtered to include only "Best Picture" nominations from the year 2000 onwards.
3.  **Data Enrichment:** To build a predictive model, we needed more than just nomination history. We enriched the dataset using external APIs:
    *   **IMDbPY & OMDb API:** Used to fetch crucial metrics for each nominated film, including:
        *   IMDb Rating
        *   Metascore
        *   Rotten Tomatoes Score (Tomatometer)
4.  **Data Cleaning:** The combined dataset was cleaned extensively. This involved handling missing values, correcting film titles, and ensuring data consistency.
5.  **Feature Creation:** We also engineered features based on other major awards, such as the Golden Globes and BAFTAs, which are often strong predictors for the Oscars.

## Machine Learning Models

### 1. Baseline Model: Logistic Regression

Our first attempt used a standard Logistic Regression model.

*   **Training:** The model was trained on data from ceremonies up to the 90th Academy Awards.
*   **Evaluation:** When tested on subsequent years, the model achieved a high accuracy (89%). However, accuracy is a misleading metric for imbalanced datasets. The classification report revealed the model's critical flaw:

    ```
                  precision    recall  f1-score   support

               0       0.89      1.00      0.94        49
               1       0.00      0.00      0.00         6

        accuracy                           0.89        55
       macro avg       0.45      0.50      0.47        55
    weighted avg       0.79      0.89      0.84        55
    ```
    The model completely failed to predict any winners (recall for class `1` is `0.00`). It simply learned to always predict the majority class (nominee).

### 2. Enhanced Model: LightGBM

To overcome the limitations of the baseline model, we switched to a more powerful algorithm and a more thoughtful approach.

*   **Algorithm:** We chose LightGBM (Light Gradient Boosting Machine), a tree-based algorithm that excels at finding complex, non-linear patterns.
*   **Handling Class Imbalance:** The key to improvement was using the `scale_pos_weight` parameter. This parameter tells the model to give significantly more weight to the minority class (winners) during training, forcing it to learn their distinguishing patterns.
*   **Feature Engineering:** A new interaction feature, `Critic_Score` (Metascore * Tomatometer), was created to capture a combined view of critic sentiment.

#### Evaluation

The LightGBM model showed a dramatic improvement:

*   **Classification Report:**
    ```
                  precision    recall  f1-score   support

               0       0.94      0.92      0.93        49
               1       0.43      0.50      0.46         6

        accuracy                           0.87        55
       macro avg       0.68      0.71      0.69        55
    weighted avg       0.88      0.87      0.88        55
    ```
    The recall for the winner class (`1`) jumped to `0.50`, meaning the model correctly identified half of the actual winners in the test set.

*   **ROC AUC Score:** The model achieved a ROC AUC score of **0.83**, which is a strong indicator of a good classifier, especially for imbalanced problems.

*   **Feature Importances:** The model revealed which factors were most predictive. Prior awards (Golden Globes, BAFTAs) and critic scores were, as expected, highly influential.

    ![LightGBM Feature Importances](https://i.imgur.com/9gL9n2H.png)

## Final Prediction & Takeaway

Using the trained LightGBM model, we predicted the win probabilities for the hypothetical 2025 Best Picture nominees.

| Film             | Win_Probability |
| ---------------- | --------------- |
| The Brutalist    | 58.96%          |
| Anora            | 36.98%          |
| Conclave         | 19.37%          |
| Dune: Part Two   | 11.07%          |
| Wicked           | 8.33%           |

**Key Takeaway:** This project is a practical case study in machine learning. It highlights that a high accuracy score can be deceptive and demonstrates the importance of choosing appropriate evaluation metrics (like recall and ROC AUC) for imbalanced datasets. By using a more suitable algorithm (LightGBM) and a specific strategy to handle class imbalance, we were able to build a far more effective and genuinely useful prediction model.

## How to Get Started

### Prerequisites

You will need Python 3 and the following libraries:
*   pandas
*   numpy
*   lightgbm
*   scikit-learn
*   matplotlib
*   seaborn
*   IMDbPY
*   requests
*   html5lib

### Installation

1.  Clone the repository.
2.  Install the required packages. It is recommended to use a virtual environment.
    ```bash
    pip install pandas numpy lightgbm scikit-learn matplotlib seaborn IMDbPY requests html5lib
    ```

### Running the Notebooks

The project is split into two main notebooks that should be run in order:

1.  **`oscar111.ipynb`**: This notebook handles the initial data collection, cleaning, and enrichment. It uses APIs to fetch data and creates the cleaned dataset (`updated_with_changes.csv`) that is used in the next step.
    *   **Note:** This notebook requires a free API key from **OMDb API** (https://www.omdbapi.com/). You will need to replace the placeholder `OMDB_API_KEY = '2121a3ae'` with your own key.
2.  **`oscar_lgbm_prediction.ipynb`**: This notebook takes the cleaned data, trains the final LightGBM model, evaluates it, and makes the final predictions.
