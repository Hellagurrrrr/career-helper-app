import { QueryClient } from "@tanstack/react-query";

// Server state for the whole app. `apiRequest` already handles token refresh, so
// we disable retries; modest staleTime avoids refetch storms without going stale.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});
