def mystery(x):
    if x > 0:
        return "positive"
    else:
        return "non-positive"
    print("done")

result = mystery(0)
print(result)



x = 15
y = x > 10 and x < 200
print(type(y))
print(y)

# Entry point is If __name__ == "__main__": ---> Look at this when begin analyzing code 


x = 15
y = x > 10 and x < 2
print(type(y))
print(y)

# You can use 'precedents of pyhton operators' to help determine which ones to run first



# AI solution below for: Return whether a given year is a leap year or not.
def is_leap_year(year):
    """
    Determines if a given year is a leap year.
    
    A year is a leap year if:
    - It is divisible by 4
    - But not by 100, unless it is also divisible by 400
    
    Args:
        year (int): The year to check
        
    Returns:
        bool: True if the year is a leap year, False otherwise
    """
    if year % 4 != 0:
        return False
    elif year % 100 != 0:
        return True
    elif year % 400 != 0:
        return False
    else:
        return True

# Get user input and check if it's a leap year
user_year = int(input("Enter a year: "))
if is_leap_year(user_year):
    print(f"{user_year} is a leap year.")
else:
    print(f"{user_year} is not a leap year.")



def check(n):
    if n % 2 == 0:
        if n % 3 == 0:
            print("n is divisible by both 2 and 3")
        else:
            print("n is divisibe by 2 but not 3")
    else:
        print(f"{n} is not divisible by 2")

check(8)
check(6)

