import hmac
import base64
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding


# Partner cert verification + key
def get_public_key_from_cert(cert_path, ca_cert_path="CA/CA.crt"):

    # Load partner cert
    with open(cert_path, "rb") as f:
        cert = x509.load_pem_x509_certificate(f.read())

    # Load CA cert
    with open(ca_cert_path, "rb") as f:
        ca_cert = x509.load_pem_x509_certificate(f.read())

    # Get CA public key
    ca_public_key = ca_cert.public_key()

    # Verify partner cert was signed by CA p
    try:
        ca_public_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.signature_hash_algorithm,
        )
        print(f"Verified:{cert_path} is valid")
    # invalid sig?
    except Exception as e:
        raise ValueError(f"Certificate Validation failed for {cert_path}: {e}")

    pem_bytes = cert.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return RSA.import_key(pem_bytes)


# 2. Sender content (Sender Side)
def build_secure_packet(message_bytes, my_private_key, partner_public_key):
    # A. Generate session keys
    aes_key = get_random_bytes(32)
    hmac_key = get_random_bytes(32)

    # B. Non-Repudiation: Sign raw message with sender's private key
    digest = SHA256.new(message_bytes)
    signature = pkcs1_15.new(my_private_key).sign(digest)

    # C. Confidentiality: Encrypt message with AES
    cipher_aes = AES.new(aes_key, AES.MODE_GCM)
    ciphertext, tag = cipher_aes.encrypt_and_digest(message_bytes)

    # D. Key Management: Encrypt session keys with receiver's RSA public key
    cipher_rsa = PKCS1_OAEP.new(partner_public_key)
    wrapped_keys = cipher_rsa.encrypt(aes_key + hmac_key)

    # E. Assemble payload block
    packet_body = wrapped_keys + cipher_aes.nonce + tag + signature + ciphertext

    # F. In-Transit Integrity: Compute HMAC over the entire packet
    transit_mac = hmac.new(hmac_key, packet_body, digestmod=SHA256).digest()

    return transit_mac + packet_body


# 3. Reciever content (Receiver Side)
def unpack_secure_packet(raw_data, my_private_key, partner_public_key):

    receiver_rsa_size = my_private_key.size_in_bytes()
    sender_rsa_size= partner_public_key.size_in_bytes()

    # A. Separate HMAC and Packet Body
    transit_hmac = raw_data[:32]
    packet_body = raw_data[32:]

    # B. Extract fixed-length headers
    wrapped_keys = packet_body[0:receiver_rsa_size]
    nonce = packet_body[receiver_rsa_size : receiver_rsa_size + 16]
    tag = packet_body[receiver_rsa_size + 16 : receiver_rsa_size + 32]
    signature = packet_body[receiver_rsa_size + 32 : receiver_rsa_size + 32 + sender_rsa_size]
    ciphertext = packet_body[receiver_rsa_size + 32 + sender_rsa_size:]

    # C. Decrypt session keys using receiver's RSA Private Key
    try:
        cipher_rsa = PKCS1_OAEP.new(my_private_key)
        decrypted_keys = cipher_rsa.decrypt(wrapped_keys)
    except ValueError:
        raise ValueError("Key mismatch")

    aes_key, hmac_key = decrypted_keys[:32], decrypted_keys[32:]

    # D. Verify In-Transit Integrity
    computed_hmac = hmac.new(hmac_key, packet_body, digestmod=SHA256).digest()
    if not hmac.compare_digest(computed_hmac, transit_hmac):
        raise ValueError("HMAC verification fail: Data was tampered in transit")

    # E. Decrypt message content using AES key
    try:
        cipher_aes = AES.new(aes_key, AES.MODE_GCM, nonce=nonce)
        message_bytes = cipher_aes.decrypt_and_verify(ciphertext, tag)
    except ValueError:
        raise ValueError("Integrity check fail")

    # F. Verify Non-Repudiation (Digital Signature)
    try:
        digest = SHA256.new(message_bytes)
        pkcs1_15.new(partner_public_key).verify(digest, signature)
    except ValueError:
        raise ValueError("Non-repudiation fail: Signature is invalid")

    return message_bytes


def decrypt_log_entry(msg, my_private_key, partner_public_key):
    sender, b64_packet = msg.split(": ", 1)
    raw_packet = base64.b64decode(b64_packet)

    decrypted_bytes = unpack_secure_packet(
            raw_packet,
            my_private_key,
            partner_public_key
        )
    return sender, decrypted_bytes.decode("utf-8")
