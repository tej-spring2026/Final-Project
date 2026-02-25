for i in range(4):
    print("Iteration:" , i)
    print("Square:" , i * i)
    print(i)


# Review Questions

# Variable Types
# x = "42" - String
# x = 42 - Interger
# x = 42.0 - Float




    
def double(number):
        """Return double the input number."""
        return number * 2

print(double(5))
print(double("Hi"))


#Escape - means don't treat the following quotation marks as special --> escape char
# Means assign 5 to variable 5
a = 5  # interger is immutable
b = a 
a = 10
print(b) # what is the value of b 
print(a)

# Use Pythontutor.com to visualize your code


# "immutable" number menas you can't change number at all 


a = [1, 2, 3] # list is mutable
b = a
a.append(4)
print(b)
print(a)
a


# What does this print
x = 10

def f():
    message = "Hello"
    x = 5 
    return x 

print(f())
print(x)
# print(message) will return an error b/c you need to directly call variable that are exist only in the function

# Draw a square
"""
🧱🧱🧱🧱
🧱🧱🧱🧱
🧱🧱🧱🧱
🧱🧱🧱🧱
"""

# Use For - loop when there's a pattern to repeat

def draw_square(size):
     for i in range(size):
          print ("🧱" * size)

draw_square(4)

# For-Loop Method Below
def draw_square(size):
    for j in range(size): 
        print("🧱" * size)


draw_square(4)

"""
Create a function to draw a triangle
🧱          1 = 0 + 1
🧱🧱        2 = 1 + 1
🧱🧱🧱      3 = 2 + 1
🧱🧱🧱🧱    4 = 3 + 1


# In row i, how many bricks are there? i + 1
"""

def draw_triangle(rows):
    for i in range(rows):
        print("🧱" * (i + 1))

draw_triangle(4)
             

"""
Draw a triangle like this (size = 5)
       i
    #  0     4 spaces + 1 # = 4
   ##  1     3 spaces + 2 # = 3
  ###  2        
 ####  3
#####
"""

# What I tried
def draw_triangle(size):
    for i in range(size):
        print( " " * (i -1) +   + "#" * (i + 1))

draw_triangle(4)

# How to actually do it
def draw_triangle(size):
    for i in range(size):
         print(" " * (size - i - 1) + "#" * (i + 1))

draw_triangle(5)

# Create a function to draw a pyramid

"""
    #      4 spaces + 1 * #
   ###     3 spaces + 3 * #
  #####    2 spaces + 5 * #
 #######   1 spaces + 7 * #

"""

