import sys
import socket
import functools
import time


listen_udp_port = int(sys.argv[1]) 
listen_tcp_port = int(sys.argv[2])


############################################### TCP IMPLEMENTATION ################################################



tcp_file_will_be_assembled = "" # I will add chunks to that string, and I will reassemble after the connection.
receiving_times = list() # Time list to print average transmission time.
ending_time = 0

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_server_socket:
    tcp_server_socket.bind(('', listen_tcp_port))               ### Bind the server socket to the port, and listen for
    tcp_server_socket.listen(1)                                 ### only one connection.
    connection , address = tcp_server_socket.accept()           ###
    with connection :
        while True:
            chunk = connection.recv(1020)                             ### Receive maximum 1020 bytes at each time, and if chunk is empty
            if not chunk:                                             ### I close connection. If chunk is not empty, I decode chunk
                ending_time = int(time.time() * 1000)                 ### into string and add string. I also keep receiving time
                break                                                 ### information.
            receiving_times.append(int(time.time() * 1000))           ###
            tcp_file_will_be_assembled += chunk.decode('utf-8')
        connection.close()
    tcp_server_socket.close()








# # #################################################### UDP IMPLEMENTATION ###################################################

# I compute checksum of string and I will compare the sent checksum and computed checksum to detect corruption.
def compute_checksum_of_string(string):
    result = 0
    for character in string:
        result += ord(character)
    return result

# I return ack value as 100 byte string which is equal to size of sequence number.
def return_ack_as_string(number):
    return '0'*(100-len(str(number))) + str(number)

# I store coming chunks here.
udp_file_will_be_assembled = list()
receiving_times_udp = list()
sending_times_udp = list()
ending_time_udp = 0
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_server_socket:
    udp_server_socket.bind(('',listen_udp_port))
    while True :
        try:
            udp_server_socket.settimeout(45)                    ##### If empty byte arrives, I close server. Or, if anything does not happen in
            data,address = udp_server_socket.recvfrom(1020)     ##### 45 seconds, I close again.
            if not data:                                        #####
                ending_time_udp = int(time.time() * 1000)
                break
            checksum = int(data[:100].decode('utf-8'))          #### I extract checksum and sequence informations from the coming packet. Then, I
            sequence = int(data[100:200].decode('utf-8'))       #### compare them with what they supposed to be. I also extract sending_time of
            sending_time = int(data[200:220].decode('utf-8'))   #### that packet.
            #### Checksum value must be equal to what we compute from arriving data.
            #### Sequence number must be equal to length of chunks list + 1. For example, if list is empty, we have to take
            #### sequence number 1 packet(sequence numbers are starting from 1), if list contains 1 element, we have to take
            #### sequence number 2 packet and so on.
            if sequence == len(udp_file_will_be_assembled)+1 and checksum == compute_checksum_of_string(data[220:].decode('utf-8')):
                # We get what we want. So, I send ack to the client and add new chunk to the previous chunks.
                # I also add times to the appropriate lists.
                ack_string = return_ack_as_string(len(udp_file_will_be_assembled) + 1)
                udp_file_will_be_assembled.append(data[220:].decode('utf-8'))
                udp_server_socket.sendto(ack_string.encode('utf-8'), address)
                receiving_times_udp.append(int(time.time()*1000))
                sending_times_udp.append(sending_time)
            else:
                # If sequence number or checksum is not correct, I send previous chunk's ack to indicate
                # I could not get what I want.
                ack_string = return_ack_as_string(len(udp_file_will_be_assembled))
                udp_server_socket.sendto(ack_string.encode('utf-8'), address)
        except (UnicodeDecodeError,ValueError):
            # Coming sequence,checksum,time information or actual data can be corrupted. So, these exceptions can be raised.
            # In these cases, I send previous chunk's ack to indicate I could not get what I want.
            ack_string = return_ack_as_string(len(udp_file_will_be_assembled))
            udp_server_socket.sendto(ack_string.encode('utf-8'), address)
        except socket.timeout:
            # If timeout exception raises, I close server.
            ending_time_udp = int(time.time() * 1000)
            break





####################################### Reassemble TCP File and Print TCP Informations ####################################################



average_times_tcp = list()
# First chunk sending time is starting time.
starting_time = int(tcp_file_will_be_assembled[:13])
all_tcp_file = ""

# I extract time and data from tcp_file_will_be_assembled string in below loop.
# Each packet time and data are in that string as 1020 byte,1020 byte ......
# For example, if coming string is 2040 byte I need 2 loop, or
# if coming string is 2000 byte, I need again 2 loop. So, I decided
# below mechanism to determine range value for 'for' loop.
range_value = len(tcp_file_will_be_assembled)//1020 if len(tcp_file_will_be_assembled) % 1020 == 0 else (len(tcp_file_will_be_assembled)//1020)+1
for i in range(range_value) :
    # First, I add actual data to all_tcp_file variable.
    # If i = 0, it will add [20:1020],or if i = 1, it will
    # add [1040:2040] and goes on like that.
    all_tcp_file += tcp_file_will_be_assembled[(i*1020)+20:(i*1020)+1020]
    # Second, I extract time information (13 byte long) and subtract it from
    # receiving time and add difference to average times list.
    average_times_tcp.append(receiving_times[i] - int(tcp_file_will_be_assembled[(i * 1020):(i * 1020) + 13]))


# I add all the transmission times and divide them by the length of the list to find average.
print('TCP Packets Average Transmission Time: ', functools.reduce(lambda a,b:a+b, average_times_tcp) / len(average_times_tcp), ' ms')
# Ending time is the time where I receive last chunk. Starting time is first packet sending time.
print('TCP Communication Total Transmission Time: ',ending_time-starting_time,' ms')



# I open new file and write the coming chunks.
with open("transfer_file_TCP.txt","w") as file:
    file.write(all_tcp_file)






####################################### Reassemble UDP File and Print UDP Informations ####################################################



# I reduce all strings into one string which is equal to all transferred UDP file.
# I already extracted time, checksum vs. from udp_file_will_be_assembled in UDP loop.
# So, it is only actual data there.
all_udp_file = functools.reduce(lambda a,b : a+b,udp_file_will_be_assembled)
# I open new file and write the coming chunks.
with open("transfer_file_UDP.txt","w") as file:
    file.write(all_udp_file)



average_times_udp = list()
for i in range(len(sending_times_udp)):
    # Extracting UDP packet sending time and subtract it from
    # receiving time and add the average times list.
    sending_times_udp[i] = int(str(sending_times_udp[i])[:13])
    average_times_udp.append(receiving_times_udp[i]-sending_times_udp[i])


# I add all the transmission times and divide them by the length of the list to find average.
print('UDP Packets Average Transmission Time: ',functools.reduce(lambda a,b:a+b,average_times_udp)/len(average_times_udp),' ms')

# Ending time is the time where I receive last chunk. Starting time is first packet sending time.
print('UDP Communication Total Transmission Time: ',ending_time_udp-sending_times_udp[0],' ms')