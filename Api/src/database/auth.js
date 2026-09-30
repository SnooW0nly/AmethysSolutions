import jwt from "jsonwebtoken";

export function generateToken(payload) {
  const JWT_SECRET = process.env.JWT_SECRET;
  if (!JWT_SECRET) throw new Error("JWT_SECRET não definido");

  return jwt.sign(
    {
      ...payload,
      iss: process.env.JWT_ISSUER || "vision-backend",
      aud: process.env.JWT_AUDIENCE || "vision-frontend",
      sub: String(payload.id),
    },
    JWT_SECRET,
    { expiresIn: "7d", algorithm: "HS256" }
  );
}

export function verifyToken(token) {
  const JWT_SECRET = process.env.JWT_SECRET;
  if (!JWT_SECRET) throw new Error("JWT_SECRET não definido");

  try {
    return jwt.verify(token, JWT_SECRET, {
      algorithms: ["HS256"],
      issuer: process.env.JWT_ISSUER || "vision-backend",
      audience: process.env.JWT_AUDIENCE || "vision-frontend",
    });
  } catch {
    return null;
  }
}