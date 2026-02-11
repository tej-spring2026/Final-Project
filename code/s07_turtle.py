import turtle

t = turtle. Turtle()
t.speed(5)
def draw_square():
    for i in range (4):
        t. forward(100)
        t. left(90)


# Use ctrl + Shf + i to turn on chatbot for AI, better than GPT








# turtle.done() # make sure the turtle graphics


# Daw a spiral shapee
def draw_spiral():
    """
   draw one square, turn an angle,then draw another square and so on
    """
    for i in range (36):
        draw_square(t, 50)
        t.left(10)
        
    
    
