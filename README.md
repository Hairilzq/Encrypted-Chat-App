# Encrypted-Chat-App
Messaging app that can send messages between a client and server. Stores past chatslogs for reviewing. Individual machines can act as either the server or client (must specify the IP address of the server on the client-side)
- To run code: 
- python3 main.py (linux)

# Contributions
- Hairil Haziq --> Developed BaseApp.py, created send_messages(), receive_messages(), main messaging loop and client-server connection
- Maniyamuthan --> Developed BaseApp.py, created write_chat_log(), view_chat_log()
- Preston --> Developed crypto_utils.py, created build_secure_packet(), unpack_secure_packet()
- Yu Yang --> Developed crypto_utils.py, created decrypt_log_entry()
- Hylann Aung --> Developed crypto_utils.py, created get_public_key_from_cert()

# OpenSSL commands
1. Create folders if not done yet
- CA
- server
- client

2. On server
- Generate CA Private Key and Self-Signed Certificate 
- openssl req -x509 -newkey rsa:4096 -sha256 -days 3650 \ -keyout CA/CA.key -out CA/CA.crt \ -passout pass:caPwd \ -subj "/C=SG/ST=West/L=Dover/O=Singapore Polytechnic/OU=SoC/CN=st2504 root CA" 

3. Generate Server Private key and CSR 
- openssl req -newkey rsa:4096 -sha256 \
  -keyout server/server.key -out server/server.csr \
  -passout pass:serverPwd \ 
  -subj "/C=SG/ST=West/L=Dover/O=Singapore Polytechnic/OU=DCDF/CN=st2504 server website" 
openssl req -newkey rsa:4096 -keyout server/server.key -out server/server.csr -sha256 -passout pass:serverPwd -subj "/C=SG/ST=West/L=Dover/O=Singapore Polytechnic/OU=DCDF/CN=st2504 server website"

4. CA sign Server CSR 
- openssl x509 -req -in server/server.csr \
  -CA CA/CA.crt -CAkey CA/CA.key -CAcreateserial \
  -passin pass:caPwd \
  -out server/server.crt -days 365 -sha256

5. On client 
- Generate Client Private key and CSR
openssl req -newkey rsa:4096 -sha256 \
  -keyout client/client.key -out client/client.csr \
  -passout pass:clientPwd \
  -subj "/C=SG/ST=West/L=Dover/O=Singapore Polytechnic/OU=DCDF/CN=st2504 client app" 

6. Send client csr to server for signing
- scp client/client.csr st2412_las@192.168.129.230:/home/st2412_las/Desktop/"Assignment - Copy"/ACG_Assignment2_v1/client/


7. On server
- CA signs CLient CSR
- openssl x509 -req -in client/client.csr \
  -CA CA/CA.crt -CAkey CA/CA.key -CAcreateserial \
  -passin pass:caPwd \
  -out client/client.crt -days 365 -sha256

8. Send signed certificates to client 
- scp client/client.crt CA/CA.crt st2412_las@192.168.129.220:/home/st2412_las/Desktop/"Assignment - Copy"/ACG_Assignment2_v1/client/

9. On client
- scp st2412_las@192.168.129.230:/home/st2412_las/Desktop/"Assignment - Copy"/ACG_Assignment2_v1/server/server.crt server/

10. verification check
- openssl verify -CAfile CA/CA.crt client/client.crt

11. On server
- verification check 
- openssl verify -CAfile CA/CA.crt server/server.crt client/client.crt

(Individual certificates/key files are not uploaded into the GitHub repo)