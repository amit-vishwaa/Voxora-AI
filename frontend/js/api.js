// Talks to the backend. The token lives in localStorage; admins can "view as" a company.
const TOKEN = "voxora_token", VIEW = "voxora_view_company";
export class ApiError extends Error { constructor(message, status) { super(message); this.status = status; } }

let unauthorized = () => {};
export const onUnauthorized = (fn) => { unauthorized = fn; };
export const getToken = () => localStorage.getItem(TOKEN);
export const setToken = (t) => (t ? localStorage.setItem(TOKEN, t) : localStorage.removeItem(TOKEN));
export const getViewCompany = () => { try { return JSON.parse(sessionStorage.getItem(VIEW)); } catch { return null; } };
export const setViewCompany = (c) => (c ? sessionStorage.setItem(VIEW, JSON.stringify({ id: c.id, name: c.name, industry: c.industry })) : sessionStorage.removeItem(VIEW));

function message(data) {
  const d = data && data.detail;
  if (Array.isArray(d)) return d.map((x) => `${(x.loc || []).slice(-1)[0] || "Field"}: ${x.msg}`).join(". ");
  return typeof d === "string" ? d : "Something went wrong. Please try again.";
}

export async function api(path, { method = "GET", body, query } = {}) {
  const url = new URL(path, location.origin);
  const view = getViewCompany();
  const scoped = !/^\/api\/(admin|auth|meta|health)/.test(path);
  if (view && scoped) url.searchParams.set("company_id", view.id);
  Object.entries(query || {}).forEach(([k, v]) => { if (v !== undefined && v !== "" && v !== null) url.searchParams.set(k, v); });
  const headers = {};
  if (getToken()) headers.Authorization = `Bearer ${getToken()}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res;
  try { res = await fetch(url, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined }); }
  catch { throw new ApiError("Cannot reach the server. Is it still running?", 0); }
  if (res.status === 401 && path !== "/api/auth/login") { unauthorized(); throw new ApiError("Please sign in again.", 401); }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(message(data), res.status);
  return data;
}

/** Send raw audio (for server-side speech-to-text). */
export async function postAudio(blob, language) {
  const res = await fetch(`/api/voice/stt?language=${language}`, { method: "POST", headers: { Authorization: `Bearer ${getToken()}`, "Content-Type": blob.type || "audio/webm" }, body: blob });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(message(data), res.status);
  return data.text || "";
}
