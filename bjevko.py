def deser(bs):
  length = len(bs)
  affixes = []
  i = 0
  depth = 0
  while (i < length):
    b = bs[i]
    i += 5
    if (i > length): raise f"unexpected end while reading length: expected at least {i - length} more bytes"
    data_len = int.from_bytes(bs[i - 4:i - 1], 'little', signed = False)
    data = (bs, i, data_len)
    i += data_len
    if (i > length): raise f"unexpected end while reading a slice: expected at least {i - length} more bytes"
    affixes.append((b, data))
    depth += int.from_bytes([b], 'little', signed = True)
    if (depth == -1): break
  if (i < length): raise f"expected end: unexpected {length - i} bytes left"
  if (depth > 0): raise f"unexpected end: expected {depth} closers"
  return affixes

def seria(affixes):
  ret = bytearray()
  for (b, data) in affixes:
    (bs, i, len) = data
    ret.append(b)
    ret.extend(len.to_bytes(4, 'little'))
    ret.extend(bs[i:i + len])
  return bytes(ret)

def to_tree(nedges, state = None):
  if (state == None): state = {'i':0}
  parent = [[], bytes()]
  while (state['i'] < len(nedges)):
    (b, data1) = nedges[state['i']]
    data = data1[0][data1[1]:data1[1]+data1[2]]
    state['i'] += 1
    if (b == 1):
      parent[0].append((data, to_tree(nedges, state)))
    else:
      parent[1] = data
      break
  return tuple(parent)