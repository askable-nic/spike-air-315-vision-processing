import { Routes, Route, useParams, Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { useSessionData } from "./hooks/useSessionData";
import { fetchExperiments, fetchSessions, Experiment } from "./lib/dataLoaders";
import { fetchManifest } from "./lib/annotationApi";
import { ManifestSession } from "./annotationTypes";
import { Layout } from "./components/Layout";
import { SessionPicker } from "./components/annotation/SessionPicker";
import { AnnotationLayout } from "./components/annotation/AnnotationLayout";
import "./App.css";

const ExperimentIndex = () => {
  const [experiments, setExperiments] = useState<readonly Experiment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExperiments()
      .then(setExperiments)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="center">Loading experiments…</div>;

  return (
    <div className="session-index">
      <h1>Experiments</h1>
      <ul>
        {experiments.map((exp) => (
          <li key={`${exp.branch}/${exp.iteration}`}>
            <Link to={`/${exp.branch}/${exp.iteration}`}>
              {exp.branch} / iteration {exp.iteration}
            </Link>
          </li>
        ))}
      </ul>
      <h2 style={{ marginTop: 32 }}>
        <Link to="/annotate">Annotate →</Link>
      </h2>
    </div>
  );
};

const SessionIndex = () => {
  const { branch, iteration } = useParams<{ branch: string; iteration: string }>();
  const [sessions, setSessions] = useState<readonly string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSessions(branch!, iteration!)
      .then(setSessions)
      .finally(() => setLoading(false));
  }, [branch, iteration]);

  if (loading) return <div className="center">Loading sessions…</div>;

  return (
    <div className="session-index">
      <h1>
        <Link to="/" className="session-index__back">Experiments</Link>
        {" / "}
        {branch} / iteration {iteration}
      </h1>
      <ul>
        {sessions.map((key) => (
          <li key={key}>
            <Link to={`/${branch}/${iteration}/${key}`}>{key.replace(/_/g, " ")}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
};

const AnnotationWorkspace = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [manifest, setManifest] = useState<ManifestSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchManifest()
      .then((sessions) => {
        const session = sessions.find((s) => s.identifier === sessionId);
        if (session) {
          setManifest(session);
        } else {
          setError(`Session "${sessionId}" not found in manifest`);
        }
      })
      .catch((err) => setError(String(err)))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) return <div className="center">Loading…</div>;
  if (error) return <div className="center error">{error}</div>;
  if (!manifest) return null;

  return <AnnotationLayout sessionId={sessionId!} manifest={manifest} />;
};

const SessionViewer = () => {
  const { branch, iteration, key } = useParams<{ branch: string; iteration: string; key: string }>();
  const { data, loading, error } = useSessionData(branch!, iteration!, key!);

  if (loading) return <div className="center">Loading session data…</div>;
  if (error) return <div className="center error">{error}</div>;
  if (!data) return null;

  return <Layout sessionKey={key!} columns={data} />;
};

export const App = () => (
  <Routes>
    <Route path="/" element={<ExperimentIndex />} />
    <Route path="/annotate" element={<SessionPicker />} />
    <Route path="/annotate/:sessionId" element={<AnnotationWorkspace />} />
    <Route path="/:branch/:iteration" element={<SessionIndex />} />
    <Route path="/:branch/:iteration/:key" element={<SessionViewer />} />
  </Routes>
);
