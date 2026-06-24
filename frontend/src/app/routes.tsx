import { createBrowserRouter, redirect } from "react-router";
import { RootLayout } from "./components/RootLayout";
import { Dashboard } from "./components/Dashboard";
import { PlanTracking } from "./components/PlanTracking";
import { Jobs } from "./components/Jobs";
import { JobTracking } from "./components/JobTracking";
import { CareerGoalLayout } from "./components/CareerGoalLayout";
import { Onboarding } from "./components/Onboarding";
import { NewGoal } from "./components/NewGoal";
import { AlumniBrowse } from "./components/AlumniBrowse";
import { AlumniDetail } from "./components/AlumniDetail";
import { Login } from "./components/Login";
import { Register } from "./components/Register";
import { ProfileEdit } from "./components/ProfileEdit";
import { Settings } from "./components/Settings";
import { AiCoaching } from "./components/AiCoaching";

export const router = createBrowserRouter(
  [
  {
    path: "/login",
    Component: Login,
  },
  {
    path: "/register",
    Component: Register,
  },
  {
    path: "/onboarding",
    Component: Onboarding,
  },
  {
    path: "/",
    Component: RootLayout,
    children: [
      { index: true, Component: Dashboard },
      { path: "applications", Component: JobTracking },
      { path: "ai-coaching", Component: AiCoaching },
      { path: "jobs", Component: Jobs },
      { path: "new-goal", Component: NewGoal },
      { path: "profile", Component: ProfileEdit },
      { path: "settings", Component: Settings },
      { path: "alumni", Component: AlumniBrowse },
      { path: "alumni/:id", Component: AlumniDetail },
      {
        path: "career-goal/:goalId",
        Component: CareerGoalLayout,
        children: [
          {
            index: true,
            loader: ({ params }) =>
              redirect(`/career-goal/${params.goalId ?? ""}/plan-tracking`),
          },
          { path: "plan-tracking", Component: PlanTracking },
          {
            path: "job-finding",
            loader: ({ params }) =>
              redirect(`/jobs?goal=${params.goalId ?? ""}`),
          },
        ],
      },
    ],
  },
  ],
  // Keep routing working under the GitHub Pages sub-path
  { basename: import.meta.env.BASE_URL },
);
