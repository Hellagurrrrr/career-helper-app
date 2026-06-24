import React from "react";
import { RouterProvider } from "react-router";
import { router } from "./routes";
import { AuthProvider } from "./lib/auth";
import { ProfileProvider } from "./lib/profile";
import { GoalsProvider } from "./lib/goals";
import { MeetingsProvider } from "./lib/alumni";
import { TrackingProvider } from "./lib/tracking";
import { NotificationsProvider } from "./lib/notifications";
import { JobApplicationsProvider } from "./lib/job-applications";
import { InterviewReviewsProvider } from "./lib/interview-reviews";
import { MockInterviewsProvider } from "./lib/mock-interviews";

export default function App() {
  return (
    <AuthProvider>
      <ProfileProvider>
        <NotificationsProvider>
          <GoalsProvider>
            <TrackingProvider>
              <MeetingsProvider>
                <JobApplicationsProvider>
                  <InterviewReviewsProvider>
                    <MockInterviewsProvider>
                      <RouterProvider router={router} />
                    </MockInterviewsProvider>
                  </InterviewReviewsProvider>
                </JobApplicationsProvider>
              </MeetingsProvider>
            </TrackingProvider>
          </GoalsProvider>
        </NotificationsProvider>
      </ProfileProvider>
    </AuthProvider>
  );
}
