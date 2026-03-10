# How to count numbers
len ([1, 2, 3, 4, 5])
# len() function counts number

# Strings vs Lists 
# Indenx, Slicing, For Loop, Len(), 

# Lists are mutable, strings are immutable
s + 'python language'
s += 'language'
# s = s + 'language' is the same as s += 'language'

# How do we sort a list in place? --> Using strings in a list
lst = ['python', 'javascript', 'r', 'cplusplus', 'c#']
lst.sort(reverse=True)

# Copying vs. Aliasing
print(lst)
# Aliasing is when two variables point to the same object in memory. No new object is created — both names are just labels for the same thing.
# Copying creates a new, independent object with the same values.


# You can use split() to split a string into a list of words; imagine being able to tokenize all characters from a book
text = "This is a sample text to demonstrate splitting into words."
words = text.split()
print(words)

# Chapter 10: Dictionaries
# A dictionary is a Mapping
names = ['Alice', 'Bob', 'Charlie']
scores = [85, 92, 78]

names_scores = list(zip(names, scores))
print(names_scores)

print(names_scores[1]) # ('Bob', 92)

# Use key to find values in a dictionary
# - Every key must be unique

# Creating and Modifying Dicts
prices = {}  # Empty dictionary
prices['APPL'] = 178.50
prices['GOOG'] = 141.80
prices['AMZN'] = 415.20

# Delete a key
del prices['GOOG']

# Update an existing key
prices['APPL'] = 180.00