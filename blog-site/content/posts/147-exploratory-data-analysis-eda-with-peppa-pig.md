---
title: "Exploratory Data Analysis (EDA) with Peppa Pig"
date: 2025-07-27T05:56:03Z
slug: exploratory-data-analysis-eda-with-peppa-pig
categories: ["Machine Learning"]
aliases: ["/post/147/"]
legacy_id: 147
---
This was a linguistic analysis project where the primary goal was not just to count words, but to evaluate the language, themes, and emotional tone of the children's show "Peppa Pig" (specifically, the first four seasons) to determine its suitability for a pre-kindergarten audience. In this study, I will try to answer a broader question:

**"Beyond a simple word list, what can a multi-faceted data analysis tell us about the show's true educational and emotional value?"**

[![[Image Placeholder 01: Peppa Pig Title]](/images/peppa1.png)](/images/peppa1.png)
 **Phase 1 & 2: Data Acquisition and Extraction**

The original dataset is a 220-page PDF of the show's transcripts of first 4 seansons. The first step involves cleaning and structuring the data using `PyPDF2` to trim irrelevant introductory pages.

Due to the original pdf page has a left and right two vertical context, I need to switch to `pdfplumber` which is another pdfplumber Python library designed specifically for extracting structured data from PDFs — especially tables and well-formatted text to manipulation (like merging/splitting pages) to handle the complex two-column layout. In addition, I noticed there are headers/footers also need to be removed, now we have a clean, structured dataset saved as a single CSV file: `season1_4_all_pages_cleaned.csv`.

[![[Image Placeholder 01: peppa1]](/images/peppa2.png)](/images/peppa2.png)

[![[Image Placeholder 02: Cleaned CSV Data]](/images/peppa3.png)](/images/peppa3.png)

```text
Text pre-processing complete.
Total words before filtering: 88497
Total words after filtering: 42566
```

**Phase 3: Initial NLP and Exploratory Data Analysis (EDA)**

Now we need to ensure the data to be ready for next step, some extra pre-processing jobs include: converting all text to lowercase, removing punctuation, and using `nltk` for tokenization. Due to the nature of this show, there are many words we need to build a custom stop word list to filter out character names like ('peppa', 'george') and sounds ('oink', 'woof'), which could improve the signal-to-noise ratio. We can use a WordCloud to have a visual sense of the most prominent terms.

[![[Image Placeholder 03: Word Cloud]](/images/peppa4.png)](/images/peppa4.png)

[![[Image Placeholder 03: Word Cloud]](/images/peppa5.png)](/images/peppa5.png)

**Phase 4: Readability Analysis – How Complex is the Language?**

Now, what about the overall language? I'll calculate readability scores to assess the text's complexity and determine the appropriate grade level for the audience. I will use two standard metrics:- Flesch-Kincaid Grade Level: Estimates the U.S. school grade level required to understand the text.
- Flesch Reading Ease: Rates text on a 100-point scale. Higher scores indicate easier-to-read material.:

```text
Flesch-Kincaid Grade Level: 2.58
Flesch Reading Ease Score: 88.85
Interpretation: Easy to read.
```

A grade level of ~2.5 means the language is simple enough for a second-grader to read. For a preschooler's \*listening\* comprehension—which is always several levels higher than their reading ability—this is the sweet spot. The language is easy to follow but still models proper sentence structure.

**Phase 5: Sentiment Analysis – What is the Emotional Tone?**

Next, I will analyze the emotional tone of the dialogue using VADER (Valence Aware Dictionary and sEntiment Reasoner), a lexicon and rule-based sentiment analysis tool specifically tuned for social media text, but it also works well on many kinds of English text. It's part of the nltk (Natural Language Toolkit) library in Python. The results a 216-to-1 positive-to-negative ratio and a complete absence of flat, neutral dialogue, the data proves this show creates an overwhelmingly positive, safe, and emotionally engaging environment for its viewers:

```text
sentiment_type
positive    216
negative      1
Name: count, dtype: int64
```

[![[Image Placeholder: Sentiment Analysis Bar Chart]](/images/peppa6.png)](/images/peppa6.png)
**Phase 6: Topic Modeling – What is the Show Actually About?**

LDA (Latent Dirichlet Allocation ) is a topic modeling technique — an unsupervised machine learning algorithm used to discover hidden thematic structures (topics) in a collection of documents. It assumes that:- Each document is a mixture of topics.
- Each topic is a mixture of words.
Here I will use LDA to help answer:
“What topics and themes of the show are present in this text data, and how are they distributed?” After refining the model to filter out noise, five distinct topics emerged:

```text
Topic 0 (Travel & Excursions): car, look, mr, everyone...
Topic 1 (Outdoor Play): muddy, boat, little, good...
Topic 2 (Toys & Imaginative Play): dinosaur, teddy, play, box...
Topic 3 (General Activities): ball, game, find, house...
Topic 4 (Social Interactions): rabbit, please, friends, hello...
```

This confirmed that the show's narrative is consistently focused on core childhood experiences: family trips, playing outside, imaginative play with toys, and polite social interaction with friends.

**Phase 7: Benchmark Analysis – How Does it Compare to a Standard?**

Finally, I returned to the classic benchmark: the Dolch Sight Words list, which is a set of 220 frequently used English words (plus 95 common nouns) that children are encouraged to recognize by sight, without needing to sound them out used in early childhood literacy (Pre-K to Grade 3). This analysis provides a more traditional academic measure.

```text
Peppa Pig season 1-4 use 208 out of 315 Dolch words.
That's an overlap of 66.03%.
```

An overlap of 66% is substantial, showing a strong alignment with foundational vocabulary for early readers. The analysis also revealed that the most common words in Peppa Pig not on the list are social words ('hello', 'mr', 'everyone') and play-related words ('dinosaur'), which reinforces the findings from the topic modeling.

**Conclusion: A Data-Driven Verdict**

This multi-faceted analysis went far beyond a simple word count. By combining readability scores, sentiment analysis, topic modeling, and a benchmark comparison, I was able to construct a complete profile of the show. The data provides a clear and conclusive answer: with its simple sentence structures, overwhelmingly positive emotional tone, and consistent focus on developmentally appropriate themes, "Peppa Pig" is an exceptionally well-suited and beneficial program for its target pre-kindergarten audience.

The full notebook and dataset are now available at [my GitHub repo](https://github.com/ZackZhouHB/zack-gitops-project/tree/editing/mlops/peppapig).
