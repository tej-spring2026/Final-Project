for i in range(5):    # Generates number from 0 to 4
    print(i)

i = 0
while i < 5: # Same thing as above but with while loop
    print(i)
    i += 1



# AI agent: Generate code that creates a simple login system 
    username = "user"
    password = "pass"
    logged_in = False

    while not logged_in:
        user_input = input("Enter username: ")
        pass_input = input("Enter password: ")
        
        if user_input == username and pass_input == password:
            print("Login successful!")
            logged_in = True
        else:
            print("Invalid credentials. Try again.")


for num in range(10):
    if num % 2 == 0:
        continue
    print(num) # This only prints odd numbers from 0 to 9


def evaluate_score(score):
