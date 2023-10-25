import sys
for line in sys.stdin:
    if "Exit" == line.strip():
        break
    print("Nada")
print("Done")