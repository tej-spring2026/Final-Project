# What happens when you call has_vowel('Python')
def has_vowel(s):
    i = 0
    while i < len(s):
        if s[i] in 'aeiou':
            i += 1
            return True
    return False

has_vowel('python')   # True?



def has_digit(s):
    for c in s:
        if c.isdigit():
            return True
        else:
            return False

print(has_digit('iPhone15'))   # True?
print(has_digit('4ever'))      # True?
print(has_digit('hello'))      # False?




def has_lower(s):
    for c in s:
        if 'c'.islower():
            return True
        else:
            return False
print(has_lower('NASA'))     # False?
print(has_lower('Python'))   # True?
print(has_lower('copilot'))  # True?

# All true b/c different variable types; string and not string



def check_vowel(s):
    for c in s:
        result = (c in 'aeiou')
    return result
print(check_vowel('orange'))   # True?
print(check_vowel('lemon'))    # False?
print(check_vowel('kiwi'))     # True?

# True, False, True
# The function only checks the last character of the string, so it will return True if the last character is a vowel and False otherwise.

def check_vowel(s):
    result_list = []
    for c in s:
        result = (c in 'aeiou')
        result_list.append(result)
    return result_list

print(check_vowel('orange'))  # [False, True, False, False, True, False]






def any_vowel(s):
    flag = False
    for c in s:
        flag = flag or (c in 'aeiou')
    return flag
print(any_vowel('rhythm'))   # False?
print(any_vowel('cafe'))     # True?
print(any_vowel('ski'))      # True?


