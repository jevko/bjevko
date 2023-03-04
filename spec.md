# bjevko-0 specification v0.1.0 draft

bjevko is a simplified binary (byte-oriented) variant of [Jevko](https://jevko.org). it can encode any valid tree structure, where nodes and edges can optionally be decorated with arbitrary data. 

bjevko is defined to be as simple as possible to (de)serialize.

bjevko serializes nodes/edges into blocks with the following structure:

```
      ____________________________________
     |         |         |                |
size | 1 byte  | 4 bytes | <length> bytes |
     |         |         |                |
name | bracket | length  |      data      |
     |_________|_________|________________|
```

* the `bracket` byte has two possible values: `1` or `-1`. `1` opens an edge to a new node, `-1` closes the current node. `1` is thus akin to an opening bracket `[`, `-1` is akin to a closing bracket `]`. these brackets must be balanced, except for an optional block with `bracket = -1` which is allowed at the end. the purpose of this block is to close the top-level tree, optionally decorating it, like other nodes, with data.

* `length` is a little-endian unsigned integer which specifies the length in bytes of `data` associated with current node/edge. 

* `data` is a sequence of arbitrary bytes of size `<length>` bytes associated with current node/edge.

## semi-formal grammar

the grammar of bjevko is as follows (in extended ABNF):

```
top = *sub [suffix]
bjevko = *sub suffix
sub = prefix bjevko
suffix = %xff affix
prefix = %x01 affix
affix = length data
length = 4(byte) ; little-endian unsigned integer
data = <length>(byte) ; sequence of arbitrary bytes of size <length>
byte = %x00-ff
```

where `<length>(byte)` means `byte` repeated exactly `length` times -- `length` is a specific value captured by the `length` rule.

## examples

for example a Jevko tree like:

```
abc[def]
```

could be serialized as follows (byte-by-byte):

```
 +1 003 'a' 'b' 'c'
 -1 003 'd' 'e' 'f'
```

the representation here is:

* bytes are separated by space.
* bracket bytes are shown as `+1` and `-1`
* the remaining bytes are shown either in decimal (`000-255`) or as ASCII characters (in quotes).

note that unlike Jevko, in bjevko brackets come before the data associated with them.

the same tree in a hypothetical variant of Jevko where that's also the case would look like this:

```
[abc]def
```

a more complex example:

```
name [Jon]
age [32]
ok [true]
colors [
  [red]
  [green]
  [blue]
]
```

is serialized as follows (here without whitespace):

```
 +1 004 'n' 'a' 'm' 'e'  -1 003 'J' 'o' 'n'
 +1 003 'a' 'g' 'e'  -1 002 '3' '2'
 +1 002 'o' 'k'  -1 004 't' 'r' 'u' 'e'
 +1 006 'c' 'o' 'l' 'o' 'r' 's'
 +1  -1 003 'r' 'e' 'd'
 +1  -1 005 'g' 'r' 'e' 'e' 'n'
 +1  -1 004 'b' 'l' 'u' 'e'
 -1
```

## deserializing bjevko

the following python function deserializes a sequence of bytes that conforms to the bjevko grammar (`bs`) into a sequence of nodes/edges:

```py
def bjevko_deserialize(bs):
  length = len(bs)
  nedges = []
  i = 0
  depth = 0
  while (i < length):
    b = bs[i]
    i += 5
    if (i > length): raise f"unexpected end while reading length: expected at least {i - length} more bytes"
    data_len = int.from_bytes(bs[i - 4:i - 1], 'little', signed = False)
    data = bs[i:i + data_len] # (bs, i, data_len)
    i += data_len
    if (i > length): raise f"unexpected end while reading a slice: expected at least {i - length} more bytes"
    nedges.append((b, data))
    depth += int.from_bytes([b], 'little', signed = True)
    if (depth == -1): break
  if (i < length): raise f"expected end: unexpected {length - i} bytes left"
  if (depth > 0): raise f"unexpected end: expected {depth} closers"
  return nedges
```

the commented out line shows how we could avoid copying by returning tuples of `(bs, i, data_len)` instead of slices in the output.

## serializing bjevko

the following python function serializes a collection of nodes/edges (`nedges`), as returned by `bjevko_deserialize`, into a sequence of bytes that conforms to the bjevko grammar:

```py
def bjevko_serialize(nedges):
  bs = bytearray()
  for (b, data) in nedges:
    bs.append(b)
    bs.extend(len(data).to_bytes(4, 'little'))
    bs.extend(data)
  return bytes(bs)
```

## converting nodes/edges to a tree structure

the following python function converts a collection of nodes/edges (`nedges`), as returned by `bjevko_deserialize`, into a tree structure of type `node = tuple[list[edge], data]`, where `edge = tuple[data, node]`.

```py
def bjevko_to_tree(nedges, state = None):
  if (state == None): state = {'i':0}
  tree = [[], bytes()]
  while (state['i'] < len(nedges)):
    (b, data) = nedges[state['i']]
    state['i'] += 1
    if (b == 1):
      tree[0].append((data, bjevko_to_tree(nedges, state)))
    else:
      tree[1] = data
      break
  return tuple(tree)
```

## mathematical foundation of bjevko

1. any unlabeled tree structure can be serialized to a word in the [Dyck language](https://en.wikipedia.org/wiki/Dyck_language).

2. a word in a Dyck language can be translated into a byte pattern, where `[` = `1` and `]` = `-1`.

3. each `[` can be associated with an edge, and each `]` with a node.

4. length-prefixed data can be appended to each `[` and `]`, associating it with the respective edge/node, effectively labeling them.

## compact variants of bjevko

bjevko, as described above, is defined so that it is as simple as possible to parse.

this forgoes possible optimizations that can dramatically improve compactness.

one such optimization is to change the structure of the node/edge to the following:

```
 ________________________________________
|                  |          |          |
|      1 byte      | <lenlen> | <length> |
|__________________|  bytes   |  bytes   |
|  1 bit  | 7 bits |          |          |
| bracket | lenlen |  length  |   data   |
|_________|________|__________|__________|
```

here the bracket byte has been replaced with a single bit, as we can very well assign `[` = `1` and `]` = `0`.

now we can use the remaining 7 bits of the first byte to store `lenlen` -- the length of `length` of data. 

data of size 0 can now fit into a single byte. data of size 1..256 can fit into size+2 bytes, data of size 257..16384 into size+3 bytes, etc. 5 bytes are enough to express lengths of up to 2^32, which is the fixed size limit used in the orignal definition of bjevko (+1). we can easily increase that limit to 2^64 or even 2^120, only using up 5 bits of the first byte.

the remaining 3 bits can be used to further shrink the length of data of size up to 16 bytes.

one sensible way of doing that is the following:

1. we use the bit pattern `00x` to represent data of size of over 17 bytes, as described above:

```
 ____________________________________________
|                      |          |          |
|        1 byte        | <lenlen> | <length> |
|______________________|  bytes   |  bytes   |
|  1 bit  |00x| 4 bits |          |          |
| bracket |   | lenlen |  length  |   data   |
|_________|___|________|__________|__________|
```

2. we use the bit pattern `01x` to represent data of size 1-16 bytes with only 1-byte overhead as follows:

```
 _________________________________
|                      |          |
|        1 byte        | <length> |
|______________________|  bytes   |
|  1 bit  |01x| 4 bits |          |
| bracket |   | length |   data   |
|_________|___|________|__________|
```

3. we use the bit pattern `10x` to squeeze data that fits into 4 bits into a single byte as follows:

```
 ______________________
|                      |
|        1 byte        |
|______________________|
|  1 bit  |10x| 4 bits |
| bracket |   |  data  |
|_________|___|________|
```

4. we reserve the remaining bit pattern `11x` for custom purposes and extensions:

```
 _________________________________
|                      |          |
|      1 byte          | <custom> |
|______________________|  bytes   |
|  1 bit  |11x| 4 bits |          |
| bracket |   | custom |  data?   |
|_________|___|________|__________|
```

this describes a compact untyped variant of bjevko. in it, we require each `x` bit to be set to `0`, reserving the value of `1` for extensions.

one obvious extension is adding support for basic datatypes.

## typed variants of bjevko

the above compact untyped variant of bjevko can be extended to support basic data types by utilizing the remaining 7 bits of the first byte as follows:

```
000 llll -- long binary string (0 or 17+ bytes) -- llll = lenlen
001 llll -- long utf-8 string (0 or 17+ bytes) -- llll = lenlen

010 llll -- short binary string (1..16 bytes) -- llll = length
011 llll -- short utf-8 string (1..16 bytes) -- llll = length

100 xxxx -- unsigned tiny int (4 bits) -- xxxx = data
101 xxxx -- signed tiny int (4 bits) -- xxxx = data

110 xxxx -- various tiny types (4 bits): -- xxxx = data
110 0000 -- boolean false
110 0001 -- boolean true
110 0010 -- <reserved>
110 0011 -- <reserved>
110 0100 -- <reserved>
110 0101 -- <reserved>
110 0110 -- <reserved>
110 0111 -- <reserved>
110 1000 -- <reserved>
110 1001 -- <reserved>
110 1010 -- <reserved>
110 1011 -- <reserved>
110 1100 -- <reserved>
110 1101 -- <reserved>
110 1110 -- <reserved>
110 1111 -- <reserved>

111 ???? -- various number types:
111 0 s ee -- integer types -- s = sign; ee = exponent
111 0 0 ee -- unsigned integer types -- ee = exponent
111 0 0 00 -- uint8
111 0 0 01 -- uint16
111 0 0 10 -- uint32
111 0 0 11 -- uint64
111 0 1 ee -- signed integer types -- ee = exponent
111 0 1 00 -- int8
111 0 1 01 -- int16
111 0 1 10 -- int32
111 0 1 11 -- int64
111 1 ? ?? -- other number types
111 1 0 00 -- <reserved>
111 1 0 01 -- <reserved>
111 1 0 10 -- <reserved>
111 1 0 11 -- <reserved>
111 1 1 00 -- <reserved>
111 1 1 01 -- <reserved>
111 1 1 10 -- float32
111 1 1 11 -- float64
```

## note: 0-padding

the compact variant of bjevko defined above should either prohibit using more bytes than necessary to express the length of data or give a special meaning to such padded values, e.g.:

```
lenlen = 1 | len = 000
lenlen = 2 | len = 000 000
lenlen = 3 | len = 000 000 000
lenlen = 3 | len = 123 000 000
...
```