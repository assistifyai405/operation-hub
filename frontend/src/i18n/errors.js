const MESSAGE_KEYS = {
  "please enter a valid email address": "validEmail",
  "this person is already a member of your organization": "alreadyMember",
  "a pending invitation already exists for this email": "pendingInvitationExists",
  "invitation not found": "invitationNotFound",
  "invitation not found or invalid": "invitationNotFound",
  "member not found": "memberNotFound",
  "you do not have permission to remove members": "cannotRemoveMembers",
  "you already own this organization": "alreadyOwner",
  "member not found in this organization": "memberNotFound",
  "job not found": "jobNotFound",
  "mailbox not found": "mailboxNotFound",
  "email not found": "emailNotFound",
  "email is not in a resolvable state": "emailNotResolvable",
  "confirm delivery before retrying — provider message id already present": "confirmDeliveryBeforeRetry",
  "failed to fetch": "network",
  "network error": "network",
  "session expired": "unauthorized",
};

const CODE_KEYS = {
  ERR_NETWORK: "network",
  NETWORK_ERROR: "network",
  RATE_LIMITED: "rateLimited",
  UNAUTHORIZED: "unauthorized",
  FORBIDDEN: "forbidden",
};

/**
 * Translate known API errors while preserving unknown server messages.
 */
export function localizeApiError(t, error, fallbackKey) {
  const message = typeof error === "string"
    ? error
    : error?.detail?.message || error?.detail || error?.message;
  const code = error?.code || error?.detail?.code || error?.response?.data?.error?.code;
  const key = (code && CODE_KEYS[String(code).toUpperCase()])
    || (typeof message === "string" && MESSAGE_KEYS[message.trim().toLowerCase()]);

  if (key) return t(`common.apiErrors.${key}`);
  if (message) return String(message);
  return t(fallbackKey || "common.error");
}
