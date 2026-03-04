# THE BELOW CODE CAN SOLVE ANY NYT SPELLING SOLVER PUZZLE. 
# IT TAKES USER INPUTS FOR THE 7 LETTERS AND THE CENTER LETTER AND THEN PRINTS AN OUTPUT OF ALL VALID WORDS WHICH FIT THE GAME'S RULES.




def uses_only(word, letters):
    """Rule 1: Word uses only the 7 given letters."""
    for c in word:
        if c not in letters:
            return False
    return True


def must_use(word, center):
    """Rule 2: Word must include the center letter."""
    return center in word


def min_length(word, min_len=4):
    """Rule 3: Word is at least 4 letters long."""
    return len(word) >= min_len


def find_words(word_list, letters, center, min_len=4):
    """
    Encapsulating function: Find all valid words that satisfy all three rules.
    
    Args:
        word_list: List of words from words.txt
        letters: String of allowed letters (e.g., 'kcboela')
        center: The center letter that must be used
        min_len: Minimum word length (default 4)
    
    Returns:
        List of valid words satisfying all three rules
    """
    valid_words = []
    for word in word_list:
        word = word.strip().lower()
        if uses_only(word, letters) and must_use(word, center) and min_length(word, min_len):
            valid_words.append(word)
    return valid_words


def main():
    """Load words from Data/words.txt and find valid spelling bee words based on user input."""
    # Load words from the words.txt file in Data folder
    with open('Data/words.txt', 'r') as f:
        word_list = f.readlines()
    
    # Get user input for the 7 letters
    while True:
        letters_input = input("Enter 7 letters (e.g., kcboela): ").strip().lower()
        if len(letters_input) != 7:
            print("Error: Please enter exactly 7 letters.")
            continue
        if not letters_input.isalpha():
            print("Error: Please enter only letters (no numbers or special characters).")
            continue
        break
    
    letters = letters_input
    
    # Get user input for the center letter
    while True:
        center = input("Enter the center letter (must be one of your 7 letters): ").strip().lower()
        if len(center) != 1:
            print("Error: Please enter exactly 1 letter.")
            continue
        if center not in letters:
            print(f"Error: Center letter '{center}' must be one of your 7 letters.")
            continue
        break
    
    min_len = 4  # Minimum word length
    
    # Find all valid words
    valid_words = find_words(word_list, letters, center, min_len)
    
    # Print results
    print(f"\n{'='*50}")
    print(f"Letters: {letters}")
    print(f"Center letter: {center}")
    print(f"Minimum length: {min_len}")
    print(f"Valid words found: {len(valid_words)}")
    print(f"{'='*50}")
    print("\nWords:")
    if valid_words:
        for word in sorted(valid_words):
            print(f"  {word}")
    else:
        print("  No valid words found.")


if __name__ == '__main__':
    main()
