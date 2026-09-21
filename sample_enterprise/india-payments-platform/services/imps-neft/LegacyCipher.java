package in.banking.imps;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

public class LegacyCipher {

    public byte[] encryptSettlementBatch(byte[] key, byte[] data) throws Exception {
        Cipher cipher = Cipher.getInstance("DESede/CBC/PKCS5Padding");
        cipher.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "DESede"));
        return cipher.doFinal(data);
    }

    public byte[] decryptSettlementBatch(byte[] key, byte[] data) throws Exception {
        Cipher cipher = Cipher.getInstance("DESede/CBC/PKCS5Padding");
        cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "DESede"));
        return cipher.doFinal(data);
    }
}
