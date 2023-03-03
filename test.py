from bjevko import deser, seria, to_tree

input = bytes([
  1, 3, 0, 0, 0, 1, 2, 3,
  255, 3, 0, 0, 0, 4, 5, 6,
  1, 3, 0, 0, 0, 1, 2, 4,
  255, 3, 0, 0, 0, 7, 8, 9,
  255, 3, 0, 0, 0, 7, 8, 9,
])
parsed = deser(input)
# print(parsed)
print(seria(parsed))
print(input)

print(to_tree(parsed))
print(to_tree(parsed))