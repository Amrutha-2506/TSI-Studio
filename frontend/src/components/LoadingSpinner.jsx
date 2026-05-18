import "../styles/LoadingSpinner.css";

export default function LoadingSpinner({ label = "Loading" }) {
  return <span className="loading-spinner" aria-label={label} role="status" />;
}
