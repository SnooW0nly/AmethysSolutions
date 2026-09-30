export function isSiteOwner(app, user) {
  try {
    return String(app?.userId) === String(user?._id || "");
  } catch {
    return false;
  }
}

export function isPermittedUser(app, user) {
  try {
    const userDiscordId = String(user?.discordId || "");
    if (!userDiscordId) return false;
    const perms = Array.isArray(app?.bot?.perms) ? app.bot.perms : [];
    return perms.includes(userDiscordId);
  } catch {
    return false;
  }
}

export function getPermissionsFlags(app, user) {
  const owner = isSiteOwner(app, user);
  // Campos restritos (token, owner): só dono do site
  // Campos livres (server, perms): dono do site OU usuário em bot.perms
  const permitted = isPermittedUser(app, user);
  const canAccessRestricted = owner;
  return {
    canAccessRestricted,
    canChangeServer: owner || permitted,
    canManagePerms: owner || permitted,
    canChangeToken: canAccessRestricted,
  };
}

/**
 * Lança erro 403 se o usuário não for dono do site.
 * Use APENAS para campos realmente restritos: token e owner.
 * Para server e perms, use isPermittedUser ou getPermissionsFlags.
 */
export function assertRestricted(app, user) {
  if (!isSiteOwner(app, user)) {
    const err = new Error("Acesso negado");
    err.status = 403;
    throw err;
  }
}