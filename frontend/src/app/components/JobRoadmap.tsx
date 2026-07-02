import React from "react";
import { Calendar, CheckCircle2, Clock } from "lucide-react";

type TimelinePhase = {
  phase: string;
  duration: string;
  status: "completed" | "in-progress" | "upcoming";
  tasks: { name: string; completed: boolean }[];
};

const TIMELINE: TimelinePhase[] = [
  {
    phase: "Preparation Phase",
    duration: "2 weeks",
    status: "completed",
    tasks: [
      { name: "Update resume and portfolio", completed: true },
      { name: "Optimize LinkedIn profile", completed: true },
      { name: "Identify target companies", completed: true },
    ],
  },
  {
    phase: "Application Phase",
    duration: "3 weeks",
    status: "in-progress",
    tasks: [
      { name: "Apply to 15-20 positions", completed: true },
      { name: "Network with industry professionals", completed: false },
      { name: "Customize cover letters", completed: false },
    ],
  },
  {
    phase: "Interview Phase",
    duration: "4 weeks",
    status: "upcoming",
    tasks: [
      { name: "Practice technical interviews", completed: false },
      { name: "Prepare behavioral questions", completed: false },
      { name: "System design mock interviews", completed: false },
    ],
  },
  {
    phase: "Offer Phase",
    duration: "2 weeks",
    status: "upcoming",
    tasks: [
      { name: "Negotiate compensation", completed: false },
      { name: "Review benefits packages", completed: false },
      { name: "Make final decision", completed: false },
    ],
  },
];

function getStatusColor(status: string) {
  switch (status) {
    case "completed":
      return "from-green-500 to-green-600";
    case "in-progress":
      return "from-blue-500 to-blue-600";
    default:
      return "from-slate-300 to-slate-400";
  }
}

function getStatusText(status: string) {
  switch (status) {
    case "completed":
      return "Completed";
    case "in-progress":
      return "In Progress";
    default:
      return "Upcoming";
  }
}

export function JobRoadmap() {
  return (
    <details className="group rounded-xl border border-slate-200/70 bg-white">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-5 py-4 text-sm font-medium text-slate-700 [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2">
          <Calendar className="h-5 w-5 text-blue-600" />
          Job search timeline
          <span className="text-xs font-normal text-slate-400">(11 weeks)</span>
        </span>
        <span className="text-xs text-slate-400 group-open:hidden">Show</span>
        <span className="hidden text-xs text-slate-400 group-open:inline">Hide</span>
      </summary>

      <div className="space-y-6 border-t border-slate-100 p-5">
        {TIMELINE.map((phase, index) => (
          <div key={index} className="relative">
            {index < TIMELINE.length - 1 && (
              <div className="absolute bottom-0 left-6 top-14 w-0.5 bg-slate-200" />
            )}
            <div className="flex gap-4">
              <div
                className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-xl bg-gradient-to-br ${getStatusColor(
                  phase.status
                )}`}
              >
                {phase.status === "completed" ? (
                  <CheckCircle2 className="h-6 w-6 text-white" />
                ) : (
                  <Clock className="h-6 w-6 text-white" />
                )}
              </div>
              <div className="flex-1 pb-6">
                <div className="mb-2 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <h3 className="font-semibold text-slate-950">{phase.phase}</h3>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="text-sm text-slate-600">{phase.duration}</span>
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-medium ${
                        phase.status === "completed"
                          ? "bg-green-50 text-green-700"
                          : phase.status === "in-progress"
                          ? "bg-blue-50 text-blue-700"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {getStatusText(phase.status)}
                    </span>
                  </div>
                </div>
                <div className="space-y-2">
                  {phase.tasks.map((task, taskIndex) => (
                    <div key={taskIndex} className="flex items-center gap-2 text-sm">
                      {task.completed ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                      ) : (
                        <div className="h-4 w-4 rounded-full border-2 border-slate-300" />
                      )}
                      <span
                        className={
                          task.completed
                            ? "text-slate-500 line-through"
                            : "text-slate-700"
                        }
                      >
                        {task.name}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </details>
  );
}
