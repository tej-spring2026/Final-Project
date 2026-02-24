

count = 0
for letter in 'mississippi':
    if letter == 's':
        count += 1
print(count)

count = 0
for c in "100 years!":
    if c == '0':
        count += 1
print(count)

n = 6
while n >= 0:
    print(n)
    n = n - 2

print('after while loop, n is', n)


# Return immidiately ends function and returns value to caller

def version_a(word):
    for letter in word:
        if letter in "aeiou":
            print(letter)
print("Done")

version_a("hello")


def version_b(word):
    for letter in word:
        if letter in "aeiou":
            return letter
    
    return "None found"

version_b("hello")


# When to use for and when to use while 
# for or while? Which loop type is better for each task?

# a. Print each character in a string
 # for
# b. Keep rolling a die until you get a 6
 # While
# c. Count the vowels in a word
# d. Ask the user for input until they type "done"

# Strings are Sequences

fruit = "banana"
fruit[0] # 'b'
fruit[1] # 'a'
fruit[2] # 'n'

fruit[0:3] # 'ban'
fruit[3:6] # 'ana'
fruit[:3] # 'ban'





# Spelling B puzzle
# - Download and bring in word.txt
# - Use a for loop 