#include <openssl/evp.h>
#include <openssl/rsa.h>
#include <openssl/sha.h>

void configure_legacy_crypto(EVP_CIPHER_CTX *context) {
    RSA *key = RSA_new();
    EVP_EncryptInit(context, EVP_aes_256_gcm(), NULL, NULL);
    SHA1((const unsigned char *)"audit", 5, NULL);
    RSA_free(key);
}
