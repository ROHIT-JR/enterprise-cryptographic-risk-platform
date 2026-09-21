const crypto = require("node:crypto");

function encryptRefreshToken(key, token) {
  const cipher = crypto.createCipheriv("aes-256-gcm", key, crypto.randomBytes(12));
  return Buffer.concat([cipher.update(token), cipher.final()]);
}

module.exports = { encryptRefreshToken };
