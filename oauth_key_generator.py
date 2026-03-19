#!/usr/bin/python
# -*-coding:utf8;-*-
# qpy:2
# ts=4:sw=4:expandtab
"""
Created on 21.03.2019

@author: reko8680
"""

import os
import fnmatch
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

encryptedpass = str.encode("myverystrongpassword")
output_dir = os.path.join(os.getcwd(), "jira_keys")


def generate_keys():
    results = [os.path.join(output_dir, n) for n in
               fnmatch.filter(os.listdir(output_dir), "*.pem") if
               os.path.isfile(os.path.join(output_dir, n))]

    if results:
        print("Public/Private RSA key pair already exists! .. Terminating")
        for key in results:
            print(key)
        return

    print("Generating new RSA keys require an adapted application link configuration in Jira")

    # Generate an RSA Keys
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )

    public_key = private_key.public_key()

    # Save the RSA private key in PEM format
    with open(os.path.join(output_dir, "rsakey.pem"), "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.BestAvailableEncryption(encryptedpass),
        )
    )

    # Save the Public key in PEM format
    with open(os.path.join(output_dir, "rsapub.pem"), "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


if __name__ == '__main__':

    generate_keys()

