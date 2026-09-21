package in.banking.imps;

import java.security.MessageDigest;

public class TransactionEncoder {

    public String legacyChecksum(byte[] payload) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-1");
        return bytesToHex(digest.digest(payload));
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
