import sys
import socket
import time


server_ip = sys.argv[1]
server_udp_port = int(sys.argv[2])
server_tcp_port = int(sys.argv[3])
client_udp_port = int(sys.argv[4])
client_tcp_port = int(sys.argv[5])



############################################### TCP IMPLEMENTATION ################################################


# fragmentation tcp file into chunks each have 1000 byte size.
fragmented_tcp_file = list()
with open("transfer_file_TCP.txt","r") as file:
    content = file.read()
    while content:
        fragmented_tcp_file.append(content[:1000])    # I will add 20 byte time information. Time info will be 13 byte length
        content = content[1000:]                      # but I allocate 20 byte space. There is nothing behind that decision.



with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as tcp_socket:
    tcp_socket.bind(('',client_tcp_port))           # Bind the socket to the client tcp port.
    tcp_socket.connect((server_ip,server_tcp_port))
    for chunks in fragmented_tcp_file:
        sending_time = str(int(time.time() * 1000)) # Adding time information to the chunk.
        chunks = sending_time + '0' * 7 + chunks    # Connect to the server, encode the strings into the bytes with utf-8 encoding and
        tcp_socket.sendall(chunks.encode('utf-8'))  # send them. After all packets finished, I exit the loop and send empty byte
    tcp_socket.sendall(b'')                         # to the server to indicate packets are finished. Server will close connection when
    tcp_socket.close()                              # empty byte arrives.







time.sleep(1)      # Server must be ready for UDP transmission, so we wait 1 seconds.








# #
# ################################################### UDP IMPLEMENTATION ###################################################
# fragmentation udp file into chunks each have 800 byte size. I will add 100 byte long checksum, 100 byte long sequence number,and 20
# byte long time information.
fragmented_udp_file = list()
with open("transfer_file_UDP.txt","r") as file:
    content = file.read()
    i = 1       # Sequence numbers start from 1 and end with length of the fragmented udp file.
    while content:
        fragmented_udp_file.append((content[:800],i)) # I add i to indicate sequence number of packet.
        content = content[800:]
        i += 1



# I return checksum value and sequence number from the same function. Checksum is simply summation of ascii values of sending string.
# I return them as '000000000000000000000000000000000checksum_value' and '000000000000000000000000000000000sequence_number'.
# So, checksum value and sequence number can be very big. There are 100 digits space for them.
def compute_checksum_and_sequence_number_as_string(string,sequence_number):
    result = 0
    for character in string:
        result += ord(character)
    return '0'*(100-len(str(result))) + str(result), '0'*(100-len(str(sequence_number))) + str(sequence_number)


packets_already_sent = list()             #### I keep list of already sending packets. So I can check re-transferred packets.
packets_sent_again = 0                    #### I keep number of re-transferred packets.

with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp_socket:
    udp_socket.bind(('',client_udp_port))
    i = 0
    while i < len(fragmented_udp_file):
        # I send string and sequence number of that string to get string
        # version of checksum and sequence number.
        checksum, sequence = compute_checksum_and_sequence_number_as_string(fragmented_udp_file[i][0],fragmented_udp_file[i][1])
        # I concatenate checksum, sequence number,time information (time is 13 byte and I add extra seven '0') and actual data.
        sending_packet = checksum + sequence + str(int(time.time()*1000)) + '0' *7 +fragmented_udp_file[i][0]
        if fragmented_udp_file[i] in packets_already_sent :
            packets_sent_again += 1                               ### If I already send packet, I increment counter. If I did not
        else:                                                     ### send before I add packet to the already sending packets.
            packets_already_sent.append(fragmented_udp_file[i])
        try:
            udp_socket.sendto(sending_packet.encode('utf-8'),(server_ip,server_udp_port)) # I send the encoded packet.
            udp_socket.settimeout(1)          # If response will not come in 1 second, I send again same packet.
            data, address = udp_socket.recvfrom(100)
            if int(data[:100].decode('utf-8')) == fragmented_udp_file[i][1] :
                i+=1      ##### If ack equals sequence number, I increment i.
            else:
                continue      # If ack is different from sequence number, I do not increment i and send the same packet again.
        except (socket.timeout,UnicodeDecodeError,ValueError):  #### Ack can be corrupted or timeout exception can be raised. In these cases,
            continue                                            #### I do not increment i and send the same packet again.
    udp_socket.sendto(b'',(server_ip,server_udp_port))  ## At the end, I send empty byte to indicate packets are finished.
    print('UDP Transmission Re-transferred Packets: ',packets_sent_again)
    udp_socket.close()