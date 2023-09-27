import numpy as np
from wifitransmitter import *
import sys
import commpy as comm
import commpy.channelcoding.convcode as check
import heapq

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

txsignal = WifiTransmitter("hello world", 2)
output = txsignal
nfft = 64
mod = comm.modulation.QAMModem(4)


demodulated_bits = mod.demodulate(output, demod_type='hard')
encoded_bits = demodulated_bits[4*nfft:] #ignores the preamble and length signals

def hard_viterbi_decoding(encoded_bits):
    #create trellis
    #00 -> [1. 0/00, 2. 1/11]
    #01 -> [1. 0/10, 2. 1/01]
    #10 -> [1. 0/11, 2. 1/00]
    #11 -> [1. 0/01, 2. 1/10]
    unique_states = [[[0,[0,0]],[1,[1,1]]], 
                     [[0,[1,0]],[1,[0,1]]], 
                     [[0,[1,1]],[1,[0,0]]], 
                     [[0,[0,1]],[1,[1,0]]]]
    num_of_states = 4
    result_length = len(encoded_bits)//2

    branch_metrics = [[0]*num_of_states*2 for _ in range(result_length)]
    
    #branch0 -> 0
    #branch1 -> 1
    #branch2 -> 2
    #branch3 -> 3
    #branch4 -> 0
    #branch5 -> 1
    #branch6 -> 2
    #branch7 -> 3
    transition2node = {0:0, 1:1, 2:2, 3:3, 4:0, 5:1, 6:2, 7:3}
    transition2input = {0:0, 1:1, 2:0, 3:1, 4:0, 5:1, 6:0, 7:1}
    node2trainsition = {0:[0,1], 1:[2,3], 2:[4,5], 3:[6,7]}
    
    for i in range(result_length):
        received_bits = encoded_bits[2*i:2*i+2]
        for stateI in range(num_of_states):
            for idx,tr in enumerate(unique_states[stateI]):
                code_bits = np.array(tr[1])
                branch_metric = np.count_nonzero(received_bits!=code_bits)
                transitionI = 2*stateI + idx
                branch_metrics[i][transitionI] = branch_metric
                #print(received_bits,code_bits,branch_metric)

    #print(branch_metrics)
    minHeap = []
    heapq.heapify(minHeap)
    info = []
    for t in range(result_length+1):
        currentState = []
        for i in range(num_of_states):
            currentState.append([float('inf'),[i, None,None]]) #node, prev_node,transition
        info.append(currentState)
    
    #print(info)
    info[0][0][0] = 0
    # heapq.heappush(minHeap,info[0][0])
    
    for t in range(result_length): #do not need to do calculations for last set of nodes 
        nodeRange = 4
        if t == 0: nodeRange = 1
        elif t == 1: nodeRange = 2
        for node in range(nodeRange):
            dist, _ = info[t][node]
            # _, _, state = currState
            for tr in node2trainsition[node]:
                nextNode = transition2node[tr]
                nextState = t + 1
                nextDist, _ = info[nextState][nextNode]
                
                newDist = dist + branch_metrics[t][tr] 
                if newDist < nextDist:
                    info[nextState][nextNode] = [newDist, [nextNode,node,tr]]

    input_bits = []
    #get node with minimum path at the end of trellis           
    idx = result_length
    distances = [stateInfo[0] for stateInfo in info[idx]]
    minNode = distances.index(min(distances))
    minTransition = info[idx][minNode][1][2]
    input_bits.append(transition2input[minTransition])

    while idx > 1:
        idx -= 1
        prevNode = minTransition//2
        minTransition = info[idx][prevNode][1][2]
        input_bits.append(transition2input[minTransition])

    input_bits = input_bits[::-1]
    print(input_bits)
    print(len(input_bits))

hard_viterbi_decoding(encoded_bits)








# cc1 = check.Trellis(np.array([3]),np.array([[0o7,0o5]]))
# preamble = np.array([1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1,1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1])
# coded_message = check.conv_encode(output[2*nfft:].astype(bool), cc1)
# coded_message = coded_message[:-6]
# print(len(coded_message))
# output = np.concatenate((output[:2*nfft],coded_message))
# output = np.concatenate((preamble, output))
# print(len(output))
# mod = comm.modulation.QAMModem(4)
# output = mod.modulate(output.astype(bool))