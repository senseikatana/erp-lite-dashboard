import type { FetchOptions } from "ofetch";

/**
 * API client.
 *
 * Adds the bearer token and the active company to every request, and turns an
 * expired session into a redirect to the login page rather than a stack of
 * failing components.
 */
export function useApi() {
  const config = useRuntimeConfig();
  const auth = useAuthStore();
  // The global i18n instance works outside component setup, unlike useI18n(),
  // which throws when this client is used from a route middleware.
  const { $i18n } = useNuxtApp();
  const router = useRouter();

  async function request<T>(
    path: string,
    options: FetchOptions = {},
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string> | undefined),
    };

    if (auth.token) {
      headers.Authorization = `Bearer ${auth.token}`;
    }

    // The company travels as a query parameter: every business row is scoped by
    // it, and making it explicit means no request can run against "whatever
    // the last request used".
    const separator = path.includes("?") ? "&" : "?";
    const withCompany = auth.activeCompany
      ? `${path}${separator}company=${encodeURIComponent(auth.activeCompany)}`
      : path;

    try {
      return await $fetch<T>(`${config.public.apiBase}${withCompany}`, {
        ...options,
        headers,
      });
    } catch (error: any) {
      if (error?.status === 401) {
        auth.clear();
        await router.push({
          path: "/login",
          query: { redirect: router.currentRoute.value.fullPath },
        });
        throw createError({
          statusCode: 401,
          statusMessage: $i18n.t("app.unauthorized"),
        });
      }

      // Surface the backend's `detail` message: the API returns specific,
      // actionable reasons such as "Role 'buyer' cannot set status PICKING".
      if (error?.data?.detail) {
        throw createError({
          statusCode: error.status ?? 400,
          statusMessage: String(error.data.detail),
        });
      }

      throw error;
    }
  }

  return {
    get: <T>(path: string, query?: Record<string, unknown>) =>
      request<T>(path, { method: "GET", query }),
    post: <T>(path: string, body?: unknown) =>
      request<T>(path, { method: "POST", body: body as any }),
    patch: <T>(path: string, body?: unknown) =>
      request<T>(path, { method: "PATCH", body: body as any }),
    delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  };
}
