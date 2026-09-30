export default function getBackendBase(req) {
  if (process.env.BACKEND_URL) return process.env.BACKEND_URL;
  const proto = (req.headers["x-forwarded-proto"] || req.protocol || "http").toString();
  const host  = (req.headers["x-forwarded-host"]  || req.get("host")).toString();
  return `${proto}://${host}`;
}