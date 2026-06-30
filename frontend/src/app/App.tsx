import React from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router";
import { router } from "./routes";
import { queryClient } from "./lib/query-client";
import { AuthProvider } from "./lib/auth";
import { GoalsProvider } from "./lib/goals";
import { TrackingProvider } from "./lib/tracking";
import { NotificationsProvider } from "./lib/notifications";
import { InterviewReviewsProvider } from "./lib/interview-reviews";
import { MockInterviewsProvider } from "./lib/mock-interviews";

// Server state lives in React Query. Domains are being migrated from context
// providers to standalone query hooks (see lib/profile.tsx for the pattern);
// only AuthProvider (session) is permanent. Each migrated domain drops a
// provider here. Still-context domains stay nested until migrated.
export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <NotificationsProvider>
          <GoalsProvider>
            <TrackingProvider>
              <InterviewReviewsProvider>
                <MockInterviewsProvider>
                  <RouterProvider router={router} />
                </MockInterviewsProvider>
              </InterviewReviewsProvider>
            </TrackingProvider>
          </GoalsProvider>
        </NotificationsProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
