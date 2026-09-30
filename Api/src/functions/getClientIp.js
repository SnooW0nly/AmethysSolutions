export default function getClientIp(req) {
  const forwarded = (req.headers["x-forwarded-for"] || "").toString();
  const chain = forwarded
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

  let ip = chain[0] || req.ip || req.connection?.remoteAddress || "";

  if (ip.startsWith("::ffff:")) {
    ip = ip.slice(7);
  }

  if (ip.startsWith("[") && ip.includes("]")) {
    ip = ip.slice(1, ip.indexOf("]"));
  }

  if (ip.includes(".") && ip.includes(":")) {
    ip = ip.split(":")[0];
  }

  if (!ip) ip = "unknown";
  return ip;
}


