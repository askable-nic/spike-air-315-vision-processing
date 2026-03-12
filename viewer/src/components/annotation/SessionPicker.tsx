import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { ManifestSession } from "../../annotationTypes";
import { fetchManifest } from "../../lib/annotationApi";
import "./SessionPicker.css";

export const SessionPicker = () => {
  const [sessions, setSessions] = useState<readonly ManifestSession[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchManifest()
      .then(setSessions)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="center">Loading sessions…</div>;

  return (
    <div className="session-index">
      <h1>
        <Link to="/" className="session-index__back">Home</Link>
        {" / "}
        Annotate
      </h1>
      <ul>
        {sessions.map((s) => (
          <li key={s.identifier}>
            <Link to={`/annotate/${s.identifier}`} className="session-picker__link">
              <span className="session-picker__name">
                {s.identifier.replace(/_/g, " ")}
              </span>
              <span className="session-picker__meta">
                {s.participant} — {s.study}
              </span>
              {s.hasBaseline && (
                <span className="session-picker__badge">baseline</span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
};
