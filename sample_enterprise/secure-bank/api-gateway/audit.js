import crypto from "node:crypto";

export function signAudit(secret, payload) {
  return crypto.createHmac("sha512", secret).update(payload).digest("hex");
}
