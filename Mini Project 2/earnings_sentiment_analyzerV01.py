# Earnings Call Sentiment Analyzer
# OIM 3640 - Mini Project 2
#
# Required third-party libraries (install before running):
#   pip install tabulate matplotlib
#
# Also required: Loughran-McDonald Master Dictionary CSV
#   Download from: https://sraf.nd.edu/loughranmcdonald-master-dictionary/
#   Look for the file named: Loughran-McDonald_MasterDictionary_1993-2024.csv
#   Place it in the same folder as this script.

import os
import re
import csv
import string
import matplotlib.pyplot as plt
from tabulate import tabulate

# ============================================================================
# CONSTANTS
# ============================================================================

# Weight given to prepared remarks vs. Q&A when combining scores
PREPARED_WEIGHT = 0.55
QA_WEIGHT = 0.45

# Weight given to hedging/uncertainty vs. tone when computing caution score
HEDGE_WEIGHT = 0.60
TONE_WEIGHT = 0.40

# Path to the LM dictionary CSV (must be in the same folder as this script)
LM_DICT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Loughran-McDonald_MasterDictionary_1993-2024.csv")

# Common financial hedge phrases to detect in transcripts
HEDGE_PHRASES = [
    "we expect", "we anticipate", "we believe", "we estimate",
    "roughly", "approximately", "subject to", "may not", "could be",
    "going forward", "we remain cautious", "uncertainty around",
    "we think", "we hope", "we project", "we forecast",
    "it is possible", "there is no assurance", "we cannot guarantee",
    "depends on", "could vary", "may differ"
]


# ============================================================================
# DATA COLLECTION
# ============================================================================

def collect_transcripts():
    """
    Prompt the user to enter one or more transcript file paths with labels.

    Returns:
        List of dicts: [{"label": "PLTR Q1 2025", "path": "/path/to/file.txt"}, ...]
    """
    transcripts = []

    print("\n" + "=" * 60)
    print("TRANSCRIPT INPUT")
    print("=" * 60)
    print("Enter the file path and a label for each earnings call transcript.")
    print("Example label: PLTR Q1 2025\n")

    while True:
        # Get the file path
        while True:
            file_path = input("Enter transcript file path: ").strip()
            if not file_path:
                print("Error: File path cannot be empty.")
                continue
            if not os.path.isfile(file_path):
                print("Error: File not found. Please check the path and try again.")
                continue
            break

        # Get the custom label
        while True:
            label = input("Enter a label for this transcript (e.g. PLTR Q1 2025): ").strip()
            if not label:
                print("Error: Label cannot be empty.")
                continue
            break

        transcripts.append({"label": label, "path": file_path})
        print(f"\n[Added] {label}")

        # Ask if the user wants to add another transcript
        while True:
            add_another = input("Add another transcript? (yes/no): ").strip().lower()
            if add_another in ["yes", "y"]:
                break
            elif add_another in ["no", "n"]:
                return transcripts
            else:
                print("Error: Please enter 'yes' or 'no'.")


# ============================================================================
# LM DICTIONARY LOADER
# ============================================================================

def load_lm_dictionary(path):
    """
    Load the Loughran-McDonald Master Dictionary from a CSV file.

    Builds three sets of words: positive, negative, and uncertainty.
    A word belongs to a set if its value in that column is greater than 0.
    Words are stored in UPPERCASE so they can be matched against uppercased tokens.

    Args:
        path: File path to the LM CSV file

    Returns:
        Tuple of (lm_positive, lm_negative, lm_uncertainty) as sets,
        or None if the file could not be loaded.
    """
    lm_positive = set()
    lm_negative = set()
    lm_uncertainty = set()

    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                word = row["Word"].strip().upper()

                # A non-zero value in a column means the word belongs to that category
                try:
                    if int(row["Positive"]) > 0:
                        lm_positive.add(word)
                except (ValueError, KeyError):
                    pass

                try:
                    if int(row["Negative"]) > 0:
                        lm_negative.add(word)
                except (ValueError, KeyError):
                    pass

                try:
                    if int(row["Uncertainty"]) > 0:
                        lm_uncertainty.add(word)
                except (ValueError, KeyError):
                    pass

        print("\n[Dictionary Loaded]")
        print(f"  Positive words:    {len(lm_positive)}")
        print(f"  Negative words:    {len(lm_negative)}")
        print(f"  Uncertainty words: {len(lm_uncertainty)}")
        return (lm_positive, lm_negative, lm_uncertainty)

    except FileNotFoundError:
        print("\n[Error] LM Dictionary file not found.")
        print(f"  Expected location: {path}")
        print("  Please download the Loughran-McDonald Master Dictionary from:")
        print("  https://sraf.nd.edu/loughranmcdonald-master-dictionary/")
        print("  Look for the file named: Loughran-McDonald_MasterDictionary_1993-2024.csv")
        print("  and place it in the same folder as this script.")
        return None
    except Exception as e:
        print(f"\n[Error] Could not load LM Dictionary: {e}")
        return None


# ============================================================================
# TEXT CLEANING
# ============================================================================

def clean_and_split_text(raw_text):
    """
    Split transcript into prepared remarks and Q&A sections, then clean each.

    Splitting is done on the phrase "questions and answers" (case-insensitive).
    If no split point is found, the entire text is treated as prepared remarks.

    Cleaning steps for each section:
      1. Lowercase
      2. Remove speaker label lines (e.g. "Alex Karp -- Chief Executive Officer")
      3. Remove punctuation
      4. Tokenize by whitespace
      5. Filter out empty strings and purely numeric tokens

    Args:
        raw_text: The full raw transcript string

    Returns:
        Dict with keys: prepared_tokens, qa_tokens, combined_tokens,
                        prepared_raw, qa_raw, combined_raw
    """
    # Split on "questions and answers" header (case-insensitive)
    split_pattern = re.compile(r'questions and answers', re.IGNORECASE)
    parts = split_pattern.split(raw_text, maxsplit=1)

    if len(parts) == 2:
        prepared_raw_text = parts[0]
        qa_raw_text = parts[1]
    else:
        # No Q&A section found -- treat entire transcript as prepared remarks
        prepared_raw_text = raw_text
        qa_raw_text = ""

    def clean_section(text):
        """
        Internal helper: clean one section of transcript text.
        Returns a tuple of (tokens_list, lowercased_raw_for_phrase_matching).
        """
        # Step 1: Lowercase
        text_lower = text.lower()

        # Step 2: Remove speaker label lines.
        # Pattern: "Firstname Lastname -- Title" at the start of a line.
        # This removes lines like "Alex Karp -- Chief Executive Officer"
        text_no_labels = re.sub(
            r'^[A-Za-z]+ [A-Za-z ]+--[^\n]+\n?',
            '',
            text_lower,
            flags=re.MULTILINE
        )

        # Keep the cleaned lowercase text (before punctuation removal)
        # for phrase matching -- punctuation-heavy text would break phrase detection
        raw_for_phrases = text_no_labels

        # Step 3: Remove punctuation
        translator = str.maketrans('', '', string.punctuation)
        text_no_punct = text_no_labels.translate(translator)

        # Step 4 & 5: Tokenize and filter
        tokens = []
        for token in text_no_punct.split():
            # Skip empty strings and purely numeric tokens (page numbers, years, etc.)
            if token and not token.isnumeric():
                tokens.append(token)

        return (tokens, raw_for_phrases)

    prepared_tokens, prepared_raw = clean_section(prepared_raw_text)
    qa_tokens, qa_raw = clean_section(qa_raw_text)

    # Combined = prepared + Q&A together
    combined_tokens = prepared_tokens + qa_tokens
    combined_raw = prepared_raw + " " + qa_raw

    return {
        "prepared_tokens": prepared_tokens,
        "qa_tokens": qa_tokens,
        "combined_tokens": combined_tokens,
        "prepared_raw": prepared_raw,
        "qa_raw": qa_raw,
        "combined_raw": combined_raw
    }


# ============================================================================
# SCORING
# ============================================================================

def compute_scores(tokens, raw_text, lm_positive, lm_negative, lm_uncertainty, hedge_phrases):
    """
    Compute sentiment and caution scores for a list of tokens.

    LM word counts: match tokens (uppercased) against each LM set.
    Hedge phrase count: search the raw_text (already lowercased) for each phrase.

    Formulas:
        net_tone    = (positive_count - negative_count) / total_words
        hedge_ratio = (uncertainty_count + hedge_phrase_count) / total_words
        caution_score = (hedge_ratio * HEDGE_WEIGHT) - (net_tone * TONE_WEIGHT)

    A higher caution score means more cautious/hedged language.
    A positive net_tone reduces the caution score (more optimistic language).

    Args:
        tokens:        List of cleaned, lowercase tokens
        raw_text:      Lowercased text string (for phrase searching)
        lm_positive:   Set of LM positive words (uppercase)
        lm_negative:   Set of LM negative words (uppercase)
        lm_uncertainty: Set of LM uncertainty words (uppercase)
        hedge_phrases: List of hedge phrase strings

    Returns:
        Dict with caution_score, net_tone, hedge_ratio, and all raw counts
    """
    total_words = len(tokens)

    # Guard against empty sections
    if total_words == 0:
        return {
            "caution_score": 0.0,
            "net_tone": 0.0,
            "hedge_ratio": 0.0,
            "positive_count": 0,
            "negative_count": 0,
            "uncertainty_count": 0,
            "hedge_phrase_count": 0,
            "total_words": 0
        }

    # Count LM word matches (uppercase the token to match the LM dictionary)
    positive_count = 0
    negative_count = 0
    uncertainty_count = 0

    for token in tokens:
        token_upper = token.upper()
        if token_upper in lm_positive:
            positive_count += 1
        if token_upper in lm_negative:
            negative_count += 1
        if token_upper in lm_uncertainty:
            uncertainty_count += 1

    # Count hedge phrase matches in the raw lowercased text
    hedge_phrase_count = 0
    for phrase in hedge_phrases:
        # Count all non-overlapping occurrences of this phrase
        hedge_phrase_count += raw_text.count(phrase)

    # Calculate the three key metrics
    net_tone = (positive_count - negative_count) / total_words
    hedge_ratio = (uncertainty_count + hedge_phrase_count) / total_words

    # Caution score: hedging raises it, positive tone lowers it
    caution_score = (hedge_ratio * HEDGE_WEIGHT) - (net_tone * TONE_WEIGHT)

    return {
        "caution_score": caution_score,
        "net_tone": net_tone,
        "hedge_ratio": hedge_ratio,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "uncertainty_count": uncertainty_count,
        "hedge_phrase_count": hedge_phrase_count,
        "total_words": total_words
    }


def score_transcript(transcript_data, lm_positive, lm_negative, lm_uncertainty, hedge_phrases):
    """
    Load and score a single transcript file.

    Computes separate scores for the prepared remarks and Q&A sections,
    then combines them into a weighted final caution score.

    Args:
        transcript_data: Dict with "label" and "path" keys
        lm_positive, lm_negative, lm_uncertainty: LM word sets
        hedge_phrases: List of hedge phrase strings

    Returns:
        Dict with all scores, counts, and metadata, or None if file read fails.
    """
    label = transcript_data["label"]
    file_path = transcript_data["path"]

    # Read the raw transcript file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
    except Exception as e:
        print(f"\n[Error] Could not read file for {label}: {e}")
        return None

    # Clean and split into sections
    sections = clean_and_split_text(raw_text)

    # Score each section separately
    prepared_scores = compute_scores(
        sections["prepared_tokens"],
        sections["prepared_raw"],
        lm_positive, lm_negative, lm_uncertainty, hedge_phrases
    )

    qa_scores = compute_scores(
        sections["qa_tokens"],
        sections["qa_raw"],
        lm_positive, lm_negative, lm_uncertainty, hedge_phrases
    )

    # Weighted combination of prepared and Q&A scores
    final_caution = (prepared_scores["caution_score"] * PREPARED_WEIGHT) + \
                    (qa_scores["caution_score"] * QA_WEIGHT)

    # Also compute net_tone and hedge_ratio for the combined text (for the table)
    combined_scores = compute_scores(
        sections["combined_tokens"],
        sections["combined_raw"],
        lm_positive, lm_negative, lm_uncertainty, hedge_phrases
    )

    return {
        "label": label,
        "path": file_path,
        "final_caution_score": final_caution,
        "prepared_caution_score": prepared_scores["caution_score"],
        "qa_caution_score": qa_scores["caution_score"],
        "net_tone": combined_scores["net_tone"],
        "hedge_ratio": combined_scores["hedge_ratio"],
        "total_words": combined_scores["total_words"],
        "prepared_word_count": prepared_scores["total_words"],
        "qa_word_count": qa_scores["total_words"],
        "positive_count": combined_scores["positive_count"],
        "negative_count": combined_scores["negative_count"],
        "uncertainty_count": combined_scores["uncertainty_count"],
        "hedge_phrase_count": combined_scores["hedge_phrase_count"]
    }


# ============================================================================
# OUTPUT: RANKED TABLE
# ============================================================================

def print_ranked_table(results):
    """
    Print a ranked comparison table of all transcripts sorted by caution score.

    The most cautious transcript (highest score) is ranked #1.

    Args:
        results: List of score dicts returned by score_transcript()
    """
    # Sort a copy by caution score (descending = most cautious first)
    sorted_results = sorted(results, key=lambda x: x["final_caution_score"], reverse=True)

    rows = []
    for rank, result in enumerate(sorted_results, start=1):
        rows.append([
            rank,
            result["label"],
            f"{result['final_caution_score']:.4f}",
            f"{result['net_tone']:.4f}",
            f"{result['hedge_ratio']:.4f}",
            result["total_words"]
        ])

    headers = ["Rank", "Quarter", "Caution Score", "Net Tone", "Hedge Ratio", "Word Count"]

    print("\n" + "=" * 60)
    print("RANKED SENTIMENT RESULTS")
    print("=" * 60)
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print("\nNote: Higher Caution Score = more hedged/cautious language detected.")
    print("      Net Tone: positive value = more positive words than negative words.")
    print("      Hedge Ratio: fraction of words/phrases flagged as uncertain or hedging.")


# ============================================================================
# OUTPUT: TREND CHART
# ============================================================================

def plot_trend(results):
    """
    Plot caution scores over time as a line chart.

    Results are displayed in their original (chronological) input order.
    A horizontal dashed line marks the mean score across all quarters.

    Args:
        results: List of score dicts in original input order
    """
    labels = [r["label"] for r in results]
    scores = [r["final_caution_score"] for r in results]
    mean_score = sum(scores) / len(scores)

    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot the caution score trend line with markers
    ax.plot(labels, scores, marker="o", linewidth=2, color="steelblue", label="Caution Score")

    # Add a dashed horizontal line at the mean
    ax.axhline(y=mean_score, color="gray", linestyle="--", linewidth=1.2, label=f"Mean: {mean_score:.4f}")

    ax.set_title("Earnings Call Caution Score Trend", fontsize=14, fontweight="bold")
    ax.set_ylabel("Caution Score (higher = more cautious)", fontsize=11)
    ax.set_xlabel("Quarter", fontsize=11)
    ax.legend()

    # Rotate x-axis labels so they don't overlap
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    # Save to the same directory as this script
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentiment_trend.png")
    plt.savefig(save_path, dpi=150)
    print(f"\n[Chart Saved] sentiment_trend.png saved to: {save_path}")

    plt.show()


# ============================================================================
# OUTPUT: SAVE RESULTS TO FILE
# ============================================================================

def save_results(results):
    """
    Optionally save a text report of all results to sentiment_results.txt.

    The file includes the ranked table and a per-quarter breakdown.

    Args:
        results: List of score dicts returned by score_transcript()
    """
    save_choice = input("\nWould you like to save the results to a file? (yes/no): ").strip().lower()

    if save_choice not in ["yes", "y"]:
        print("Results not saved.")
        return

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sentiment_results.txt")

    # Sort by caution score descending for the file
    sorted_results = sorted(results, key=lambda x: x["final_caution_score"], reverse=True)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("EARNINGS CALL SENTIMENT ANALYZER - RESULTS\n")
            f.write("=" * 60 + "\n\n")

            # Ranked table
            f.write("RANKED COMPARISON TABLE\n")
            f.write("-" * 60 + "\n")
            rows = []
            for rank, result in enumerate(sorted_results, start=1):
                rows.append([
                    rank,
                    result["label"],
                    f"{result['final_caution_score']:.4f}",
                    f"{result['net_tone']:.4f}",
                    f"{result['hedge_ratio']:.4f}",
                    result["total_words"]
                ])
            headers = ["Rank", "Quarter", "Caution Score", "Net Tone", "Hedge Ratio", "Word Count"]
            f.write(tabulate(rows, headers=headers, tablefmt="grid"))
            f.write("\n\n")

            # Per-quarter breakdown
            f.write("PER-QUARTER DETAIL BREAKDOWN\n")
            f.write("-" * 60 + "\n\n")
            for result in sorted_results:
                f.write(f"Quarter:              {result['label']}\n")
                f.write(f"File:                 {result['path']}\n")
                f.write(f"Final Caution Score:  {result['final_caution_score']:.4f}\n")
                f.write(f"  Prepared Remarks:   {result['prepared_caution_score']:.4f} (weight: {PREPARED_WEIGHT})\n")
                f.write(f"  Q&A Section:        {result['qa_caution_score']:.4f} (weight: {QA_WEIGHT})\n")
                f.write(f"Net Tone:             {result['net_tone']:.4f}\n")
                f.write(f"Hedge Ratio:          {result['hedge_ratio']:.4f}\n")
                f.write(f"Total Word Count:     {result['total_words']}\n")
                f.write(f"  Prepared Words:     {result['prepared_word_count']}\n")
                f.write(f"  Q&A Words:          {result['qa_word_count']}\n")
                f.write(f"Positive Word Count:  {result['positive_count']}\n")
                f.write(f"Negative Word Count:  {result['negative_count']}\n")
                f.write(f"Uncertainty Words:    {result['uncertainty_count']}\n")
                f.write(f"Hedge Phrase Hits:    {result['hedge_phrase_count']}\n")
                f.write("\n" + "-" * 40 + "\n\n")

        print(f"[Saved] Results written to: {output_path}")

    except Exception as e:
        print(f"[Error] Could not save results: {e}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Main function: orchestrates the full analysis workflow.
    """
    print("\n" + "=" * 60)
    print("  EARNINGS CALL SENTIMENT ANALYZER")
    print("  OIM 3640 - Mini Project 2")
    print("=" * 60)
    print("This tool analyzes earnings call transcripts for shifts")
    print("in language tone and hedging behavior over time.\n")

    # Load the LM dictionary -- required for scoring
    lm_result = load_lm_dictionary(LM_DICT_PATH)
    if lm_result is None:
        print("\n[Exiting] Please download and place the LM dictionary file before running.")
        return

    lm_positive, lm_negative, lm_uncertainty = lm_result

    # Collect transcript file paths from the user
    transcripts = collect_transcripts()

    if not transcripts:
        print("\nNo transcripts entered. Exiting.")
        return

    # Score each transcript
    print("\n" + "=" * 60)
    print("ANALYZING TRANSCRIPTS...")
    print("=" * 60)

    results = []
    for transcript in transcripts:
        print(f"\nProcessing: {transcript['label']}...")
        result = score_transcript(transcript, lm_positive, lm_negative, lm_uncertainty, HEDGE_PHRASES)
        if result is not None:
            results.append(result)
            print(f"  Done. Caution Score: {result['final_caution_score']:.4f} | Words: {result['total_words']}")

    if not results:
        print("\n[Error] No transcripts were successfully scored. Exiting.")
        return

    # Print ranked comparison table
    print_ranked_table(results)

    # Optionally show the trend chart
    if len(results) >= 2:
        while True:
            show_chart = input("\nWould you like to see the caution score trend chart? (yes/no): ").strip().lower()
            if show_chart in ["yes", "y"]:
                plot_trend(results)
                break
            elif show_chart in ["no", "n"]:
                break
            else:
                print("Please enter 'yes' or 'no'.")
    else:
        print("\n(Add at least 2 transcripts to generate a trend chart.)")

    # Optionally save results to file
    save_results(results)

    print("\n" + "=" * 60)
    print("Analysis complete. Thank you for using the Earnings Call Sentiment Analyzer!")
    print("=" * 60)


if __name__ == "__main__":
    main()
