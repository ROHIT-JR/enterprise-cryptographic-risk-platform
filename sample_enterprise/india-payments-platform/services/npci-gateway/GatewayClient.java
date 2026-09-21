package in.npci.gateway;

import javax.net.ssl.SSLContext;
import java.security.KeyPairGenerator;
import java.security.Signature;

public class GatewayClient {

    public SSLContext createContext() throws Exception {
        SSLContext context = SSLContext.getInstance("TLSv1.2");
        context.init(null, null, null);
        return context;
    }

    public KeyPairGenerator ecdsaKeyGenerator() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("EC");
        generator.initialize(256);
        return generator;
    }

    public Signature ecdsaSigner() throws Exception {
        return Signature.getInstance("SHA256withECDSA");
    }
}
