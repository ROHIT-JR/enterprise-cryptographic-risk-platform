#include <openssl/evp.h>
#include <openssl/rsa.h>

int legacy_sign(EVP_PKEY *key, const unsigned char *data, size_t len, unsigned char *sig) {
    EVP_MD_CTX *ctx = EVP_MD_CTX_new();
    EVP_DigestSignInit(ctx, NULL, EVP_sha256(), NULL, key);
    return EVP_DigestSign(ctx, sig, &len, data, len);
}
