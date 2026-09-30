export async function fetchAdminUserById(userId: string): Promise<any | null> {
  if (!userId) return null;
  const qs = new URLSearchParams({ search: userId, limit: "1" });
  const res = await fetch(`/api/admin/users?${qs.toString()}`, { cache: "no-store" });
  if (!res.ok) return null;
  const data = await res.json();
  const users = Array.isArray(data?.users) ? data.users : [];
  return users[0] || null;
}


