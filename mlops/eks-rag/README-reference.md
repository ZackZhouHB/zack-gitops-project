# Peppa Pig Transcript Analysis

This project analyzes the transcripts of the first four seasons of the children's show "Peppa Pig" to understand its vocabulary, themes, and suitability for a pre-school audience.

## Introduction

The goal of this project is to perform a comprehensive analysis of the language used in "Peppa Pig" to determine its educational value and appropriateness for young children. The analysis is based on the transcripts of the first four seasons of the show, which were extracted from a PDF file.

## Data Extraction and Pre-processing

The transcripts were extracted from a PDF file (`peppa.pdf`) using the `pypdf` and `pdfplumber` libraries in Python. The text was then cleaned and pre-processed by:

*   Converting all text to lowercase.
*   Removing punctuation and special characters.
*   Tokenizing the text into individual words.
*   Removing common English stop words and custom stop words specific to the show.

The cleaned data was saved to a CSV file (`season1_4_all_pages_cleaned.csv`).

## Exploratory Data Analysis (EDA)

The EDA was performed to understand the word frequencies in the transcripts. The most common words were visualized using a word cloud and a bar chart. The analysis revealed that the most frequent words are simple, action-oriented, and related to family and play, which is appropriate for a pre-school audience.

## Readability Analysis

A readability analysis was conducted to assess the complexity of the text and determine the appropriate grade level for the audience. The Flesch-Kincaid Grade Level and Flesch Reading Ease scores were calculated, which confirmed that the language is simple and accessible for young children.

## Sentiment Analysis

A sentiment analysis was performed to gauge the overall emotional tone of the show. The analysis revealed that the overwhelming sentiment is positive and neutral, with very few instances of negative language. This suggests a consistently cheerful and safe emotional tone.

## Topic Modeling

Latent Dirichlet Allocation (LDA) was used to identify the main topics or underlying themes in the series. The analysis revealed that the topics revolve around common childhood themes such as playing outside, family activities, visiting places, and learning new things.

## Conclusion

The data-driven analysis confirms that the language, themes, and emotional tone of "Peppa Pig" are highly suitable for its target pre-kindergarten audience.

## How to Run

To run the analysis, you can use the following Jupyter Notebooks:

*   `EDA-1st.ipynb`: This notebook contains the code for data extraction and pre-processing.
*   `EDA-PeppaPig.ipynb`: This notebook contains the code for the in-depth analysis of the transcripts.

You will need to install the required libraries, which are listed in the notebooks.
