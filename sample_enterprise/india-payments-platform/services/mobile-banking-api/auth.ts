import { createHmac } from "node:crypto";

export function signToken(secret: string, payload: string): string {
  return createHmac("sha256", secret).update(payload).digest("hex");
}

export function verifyToken(secret: string, payload: string, signature: string): boolean {
  return signToken(secret, payload) === signature;
}
