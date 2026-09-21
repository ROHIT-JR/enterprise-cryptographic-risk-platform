package in.npci.gateway;

import org.bouncycastle.jce.provider.BouncyCastleProvider;
import java.security.MessageDigest;
import java.security.Security;

public class CertificateManager {

    public void registerProvider() {
        Security.addProvider(new BouncyCastleProvider());
    }

    public byte[] certificateFingerprint(byte[] certBytes) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        return digest.digest(certBytes);
    }
}
