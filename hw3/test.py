import struct 
f = open("Carnegie_Mellon_University.jpg","rb")
data = f.read()
#print(data)

seq1 = data[0:128]
seq2 = data[128:256]

l = [seq1, seq2]
print(seq1)
print()
print(seq2)

concatenated_sequence = bytes().join(l)
print()
print(concatenated_sequence)


# # print(type(data))
# f.close()

# packed_data = struct.pack("10240s", data)
# unpacked_data = struct.unpack("10240s", packed_data)
# print("NEW SHIT")
# print(unpacked_data[0][1024:2048])
