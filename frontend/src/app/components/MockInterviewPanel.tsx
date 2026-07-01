import React from "react";
import {
  Mic,
  Volume2,
  Loader2,
  Play,
  Square,
  Sparkles,
  MessageSquare,
  Send,
} from "lucide-react";
import { CoachingFeedbackResults } from "./CoachingFeedbackResults";
import {
  getSpeechRecognitionCtor,
  MOCK_QUESTION_COUNT,
  MockInterviewContext,
  MockInterviewSession,
  MockInterviewTurn,
  speakCoachLine,
  startServerMockInterview,
  stopCoachSpeech,
  submitServerMockTurn,
  useMockInterviews,
} from "../lib/mock-interviews";

type Phase = "idle" | "coach_speaking" | "ready" | "recording" | "evaluating" | "complete";

function newTurn(role: "coach" | "user", text: string): MockInterviewTurn {
  return {
    id:
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `t-${Date.now()}`,
    role,
    text,
    timestamp: Date.now(),
  };
}

export function MockInterviewPanel({ context }: { context: MockInterviewContext }) {
  const { getSessionsForApplication, saveSession, deleteSession } = useMockInterviews();
  const archived = getSessionsForApplication(context.applicationId);

  const [phase, setPhase] = React.useState<Phase>("idle");
  const [questionIndex, setQuestionIndex] = React.useState(0);
  const [turns, setTurns] = React.useState<MockInterviewTurn[]>([]);
  const [startedAt, setStartedAt] = React.useState(0);
  const [liveTranscript, setLiveTranscript] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [completedSession, setCompletedSession] = React.useState<MockInterviewSession | null>(
    null
  );
  const [voiceReady, setVoiceReady] = React.useState(false);
  const [serverSessionId, setServerSessionId] = React.useState<string | null>(null);
  const [totalQuestions, setTotalQuestions] = React.useState(MOCK_QUESTION_COUNT);

  const recognitionRef = React.useRef<SpeechRecognition | null>(null);
  const turnsRef = React.useRef<MockInterviewTurn[]>([]);
  const questionIndexRef = React.useRef(0);

  React.useEffect(() => {
    turnsRef.current = turns;
  }, [turns]);

  React.useEffect(() => {
    questionIndexRef.current = questionIndex;
  }, [questionIndex]);

  React.useEffect(() => {
    const Recognition = getSpeechRecognitionCtor();
    const tts = typeof window !== "undefined" && !!window.speechSynthesis;
    setVoiceReady(!!Recognition && tts);
    return () => {
      stopCoachSpeech();
      recognitionRef.current?.abort();
    };
  }, []);

  const speakAndWait = (text: string) => {
    setTurns((prev) => {
      const next = [...prev, newTurn("coach", text)];
      turnsRef.current = next;
      return next;
    });
    setPhase("coach_speaking");
    speakCoachLine(text, () => setPhase("ready"));
  };

  const askQuestion = (index: number, text: string) => {
    setQuestionIndex(index);
    questionIndexRef.current = index;
    speakAndWait(text);
  };

  const startInterview = async () => {
    if (!voiceReady) {
      setError(
        "Voice coaching requires speech synthesis and recognition (Chrome or Edge recommended)."
      );
      return;
    }
    setError(null);
    setCompletedSession(null);
    setTurns([]);
    turnsRef.current = [];
    setLiveTranscript("");
    setStartedAt(Date.now());
    try {
      const started = await startServerMockInterview(context.applicationId);
      setServerSessionId(started.sessionId);
      setTotalQuestions(started.totalQuestions);
      askQuestion(started.questionIndex, started.question);
    } catch {
      setError("Could not start the mock interview. Try again.");
      setPhase("idle");
    }
  };

  const startRecording = () => {
    const Recognition = getSpeechRecognitionCtor();
    if (!Recognition) return;
    recognitionRef.current?.abort();
    setLiveTranscript("");
    const recognition = new Recognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognitionRef.current = recognition;

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let text = "";
      for (let i = 0; i < event.results.length; i++) {
        text += event.results[i][0].transcript;
      }
      setLiveTranscript(text.trim());
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const reason: Record<string, string> = {
        "not-allowed":
          "Microphone access is blocked. Allow mic permission for this site in your browser, then tap record again.",
        "service-not-allowed":
          "Speech recognition is blocked. Allow mic permission for this site, then tap record again.",
        "audio-capture": "No microphone was found. Connect a mic and try again.",
        "no-speech": "No speech was detected. Speak clearly into your mic, then tap record again.",
        "network":
          "Speech recognition needs an internet connection (Chrome streams the audio to Google to transcribe).",
        "aborted": "Recording was interrupted. Tap record to try again.",
      };
      setError(
        reason[event.error] ??
          `Recording failed (${event.error}). Voice answers need Chrome or Edge with microphone access.`
      );
      setPhase("ready");
    };

    try {
      recognition.start();
      setPhase("recording");
    } catch {
      setError(
        "Could not start recording. Check that your browser allows microphone access for this site (Chrome or Edge recommended)."
      );
      setPhase("ready");
    }
  };

  const submitAnswer = async () => {
    recognitionRef.current?.abort();
    const answer = liveTranscript.trim();
    if (!answer) {
      setError("No speech detected. Try speaking again or type is not supported in this demo.");
      setPhase("ready");
      return;
    }
    setError(null);
    setLiveTranscript("");

    const updated = [...turnsRef.current, newTurn("user", answer)];
    setTurns(updated);
    turnsRef.current = updated;

    if (!serverSessionId) {
      setError("Mock interview session was not created. Start again.");
      setPhase("idle");
      return;
    }

    try {
      const response = await submitServerMockTurn(context.applicationId, serverSessionId, answer);
      if (response.status === "in_progress" && response.question != null && response.questionIndex != null) {
        window.setTimeout(() => askQuestion(response.questionIndex ?? 0, response.question ?? ""), 500);
        return;
      }
      if (response.session) {
        saveSession(response.session);
        setCompletedSession(response.session);
        setPhase("complete");
      }
    } catch {
      setError("Could not submit your answer. Try again.");
      setPhase("ready");
    }
  };

  const finishSession = async () => {
    setPhase("evaluating");
    stopCoachSpeech();
    recognitionRef.current?.abort();
    void startedAt;
    try {
      if (!serverSessionId) throw new Error("No server session.");
      const response = await submitServerMockTurn(context.applicationId, serverSessionId, "", true);
      if (response.session) {
        saveSession(response.session);
        setCompletedSession(response.session);
        setPhase("complete");
      } else {
        setPhase("ready");
      }
    } catch {
      setError("Evaluation failed. Please try again.");
      setPhase("idle");
    }
  };

  const endEarly = () => {
    stopCoachSpeech();
    recognitionRef.current?.abort();
    if (turnsRef.current.filter((t) => t.role === "user").length > 0) {
      void finishSession();
    } else {
      setPhase("idle");
      setTurns([]);
      turnsRef.current = [];
    }
  };

  const resetToIdle = () => {
    setPhase("idle");
    setCompletedSession(null);
    setTurns([]);
    turnsRef.current = [];
    setQuestionIndex(0);
    setServerSessionId(null);
    setLiveTranscript("");
  };

  const busy = phase === "coach_speaking" || phase === "evaluating";

  return (
    <div className="space-y-4">
      <p className="text-xs leading-relaxed text-slate-500">
        Practice a live mock interview for{" "}
        <span className="font-medium text-slate-700">{context.jobTitle}</span>. The AI coach
        speaks questions aloud; record your voice answers. After {MOCK_QUESTION_COUNT} prompts
        you receive scored feedback. Each session is archived (demo — browser speech APIs).
      </p>

      {!voiceReady && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
          Voice input/output may be limited in this browser. Use Chrome or Edge for the full
          experience.
        </p>
      )}

      {phase === "idle" && (
        <button
          type="button"
          onClick={startInterview}
          className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700 sm:w-auto"
        >
          <Play className="h-4 w-4" />
          Start mock interview
        </button>
      )}

      {phase !== "idle" && phase !== "complete" && (
        <div className="rounded-xl border border-indigo-100 bg-indigo-50/30 p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-2 text-sm font-semibold text-indigo-900">
              {phase === "coach_speaking" && (
                <>
                  <Volume2 className="h-4 w-4 animate-pulse" />
                  Coach speaking…
                </>
              )}
              {phase === "ready" && (
                <>
                  <Mic className="h-4 w-4" />
                  Ready for your answer
                </>
              )}
              {phase === "recording" && (
                <>
                  <Mic className="h-4 w-4 animate-pulse text-red-600" />
                  Recording…
                </>
              )}
              {phase === "evaluating" && (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Evaluating your performance…
                </>
              )}
            </span>
            <span className="text-xs text-slate-500">
              Q {Math.min(questionIndex + 1, totalQuestions)}/{totalQuestions}
            </span>
          </div>

          <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-slate-200 bg-white p-3">
            {turns.map((t) => (
              <div
                key={t.id}
                className={`text-sm leading-relaxed ${
                  t.role === "coach" ? "text-indigo-900" : "text-slate-800"
                }`}
              >
                <span className="font-semibold">
                  {t.role === "coach" ? "Coach" : "You"}:
                </span>{" "}
                {t.text}
              </div>
            ))}
            {liveTranscript && (
              <p className="text-sm italic text-slate-500">…{liveTranscript}</p>
            )}
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {phase === "ready" && (
              <button
                type="button"
                onClick={startRecording}
                className="inline-flex items-center gap-2 rounded-lg bg-white px-3 py-2 text-sm font-medium text-indigo-900 ring-1 ring-indigo-200 hover:bg-indigo-50"
              >
                <Mic className="h-4 w-4" />
                Record answer
              </button>
            )}
            {phase === "recording" && (
              <button
                type="button"
                onClick={submitAnswer}
                className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
              >
                <Send className="h-4 w-4" />
                Submit answer
              </button>
            )}
            <button
              type="button"
              disabled={busy}
              onClick={endEarly}
              className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <Square className="h-3.5 w-3.5" />
              End early
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="text-xs font-medium text-red-700" role="alert">
          {error}
        </p>
      )}

      {completedSession && (
        <div className="rounded-xl border border-green-100 bg-white p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-green-800">
            <Sparkles className="h-4 w-4" />
            Mock interview complete — archived
          </div>
          <CoachingFeedbackResults
            subtitle={`${Math.round(completedSession.durationSec / 60)} min · ${new Date(completedSession.completedAt).toLocaleString()}`}
            overallSummary={completedSession.overallSummary}
            dimensions={completedSession.dimensions}
            improvementAdvice={completedSession.improvementAdvice}
            transcript={completedSession.transcript}
          />
          <button
            type="button"
            onClick={resetToIdle}
            className="mt-3 text-sm font-medium text-indigo-700 hover:underline"
          >
            Start another mock
          </button>
        </div>
      )}

      {archived.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Archived mock interviews ({archived.length})
          </h4>
          {archived.map((session) => (
            <details
              key={session.id}
              className="rounded-xl border border-slate-200 bg-slate-50/50 p-3"
            >
              <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-medium text-slate-800">
                <MessageSquare className="h-4 w-4 shrink-0 text-indigo-600" />
                <span className="min-w-0 flex-1 truncate">
                  Mock · {Math.round(session.durationSec / 60)} min
                </span>
                <span className="shrink-0 text-xs text-slate-500">
                  {new Date(session.completedAt).toLocaleDateString()}
                </span>
              </summary>
              <div className="mt-3 border-t border-slate-200 pt-3">
                <CoachingFeedbackResults
                  overallSummary={session.overallSummary}
                  dimensions={session.dimensions}
                  improvementAdvice={session.improvementAdvice}
                  transcript={session.transcript}
                  onDelete={() => {
                    deleteSession(session.id);
                    if (completedSession?.id === session.id) setCompletedSession(null);
                  }}
                />
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
