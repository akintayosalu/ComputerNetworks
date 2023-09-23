import numpy as np
from wifitransmitter import *

def binary_decode(row):
    if np.count_nonzero(row==1) >= 2:
        return 1.0
    else:
        return 0.0

def WifiReceiver(output, level):
    if level >= 1:
        nfft = 64
        Interleave = np.reshape(np.transpose(np.reshape(np.arange(1, 2*nfft+1, 1),[-1,4])),[-1,])

        #Get length of message
        length_binary = output[0:2*nfft]
        encoded_length = np.reshape(np.trim_zeros(length_binary),[-1,3])
        decoded_length = np.apply_along_axis(binary_decode, axis=1, arr=encoded_length) #decode length bits
        length = int(''.join(map(lambda x: str(int(x)), decoded_length)), 2)

        #Get message by "un-interleaving the message"
        raw_output = output[2*nfft:]
        output_length = len(raw_output)
        nsym = int(output_length/(2*nfft))
        initial_input = np.zeros(shape=(output_length,))

        for i in range(nsym):
            initial_input[(i*(2*nfft))+Interleave-1] = raw_output[i*2*nfft:(i+1)*2*nfft]

        num_of_added_zeros = 2*nfft-(length*8)%(2*nfft)
        unpadded_input = initial_input[:output_length-num_of_added_zeros].astype(int)
        decimal_input = np.packbits(np.reshape(unpadded_input,[-1,8])) #binary -> 8-bit unsigned integer 

        message = "" #get message by turning ASCII -> characters
        for i in decimal_input:
            message += chr(i)
        message_length = len(message)
        begin_zero_padding = 0
        return begin_zero_padding, message, message_length


# if __name__ == '__main__':
#     if len(sys.argv)<2:
#         raise Exception("Error: Not enough arguments were provided")
#     elif len(sys.argv)>3:
#         raise Exception("Error: Too many arguments were provided")
#     else:
#         WifiReceiver(sys.argv[1], sys.argv[2])

txsignal = WifiTransmitter("hello world", 1)
begin_zero_padding, message, message_length = WifiReceiver(txsignal, 1)
print(begin_zero_padding, message, message_length)