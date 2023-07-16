from datetime import datetime

now = datetime.now()

current_time = now.strftime("%H:%M:%S")
print("Current Time =", current_time)
print("test")
with open('readme.txt', 'w') as f:
    f.write(f'test: Time: {current_time}')