age = int(input('What is you age?  >>'))

if age < 21:
    print("No, you cannot get sloshed.")
elif age > 65:
    print('You are too old for this.')
else:
    print("Yes, you can get sloshed.")


# Conditional Statemnets: Order matter b/c first matching condition wins


# score == 91

if score >= 80:
    print("B")
elif score >= 90:
    print("A")
elif score >= 70:
    print("C")
else:
    print("F")



