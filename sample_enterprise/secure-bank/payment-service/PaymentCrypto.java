package com.securebank.payments;

import java.security.KeyPairGenerator;
import javax.crypto.Cipher;
import javax.crypto.KeyAgreement;
import org.bouncycastle.jce.provider.BouncyCastleProvider;

public final class PaymentCrypto {
    public void configure() throws Exception {
        Cipher.getInstance("AES/GCM/NoPadding");
        Cipher.getInstance("DESede/CBC/PKCS5Padding");
        KeyPairGenerator.getInstance("RSA").initialize(3072);
        KeyPairGenerator.getInstance("EC");
        KeyAgreement.getInstance("DH");
        new BouncyCastleProvider();
    }
}
