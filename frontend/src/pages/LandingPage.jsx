import React from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  BookOpen,
  Check,
  ChevronDown,
  FileText,
  HelpCircle,
  ListChecks,
  LogOut,
  Mail,
  MailSearch,
  MessageSquare,
  PencilLine,
  SendHorizontal,
  Settings,
  Sparkles,
  UserCircle,
} from "lucide-react";
import { parseEmailThread } from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";
import { createLocalSession } from "../utils/localEmailTools";
import "../styles/LandingPage.css";

const demoThread = `From: Lakisha Williams <lakisha@example.com>
Sent: May 3, 2026, 9:14 AM
To: Georgia Natural Gas Customer Care
Subject: Your GNG bill is ready for viewing

Please advise why the bill is $395.66. This is much higher than expected.

From: GNG Customer Service <customercare@gng.com>
Sent: May 12, 2026, 10:22 AM
To: Lakisha Williams
Subject: RE: Your GNG bill is ready for viewing

Thank you for contacting Georgia Natural Gas. Please provide the account number or full service address so we can review the billing details.

From: Lakisha Williams <lakisha@example.com>
Sent: May 12, 2026, 11:05 AM
To: Georgia Natural Gas Customer Care
Subject: RE: Your GNG bill is ready for viewing

Our new address is 140 Old Fairburn Close SW, Atlanta, GA 30331. Please explain why the bill is $395.66.`;

const features = [
  {
    icon: <MailSearch size={32} />,
    title: "Analyze",
    desc: "Break down the email thread and identify the core issue.",
  },
  {
    icon: <ListChecks size={32} />,
    title: "Summarize",
    desc: "Get a summary for each email in the conversation.",
  },
  {
    icon: <PencilLine size={32} />,
    title: "Generate Reply",
    desc: "Create a professional, detailed, and editable reply.",
  },
  {
    icon: <FileText size={32} />,
    title: "Review & Edit",
    desc: "Review, edit, and copy the reply before sending.",
  },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [emailThread, setEmailThread] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [error, setError] = React.useState("");

  async function handleEmailSubmit(event) {
    event.preventDefault();
    const trimmedThread = emailThread.trim();
    if (!trimmedThread) {
      setError("Paste a customer email thread before continuing.");
      return;
    }

    setIsSubmitting(true);
    setError("");
    sessionStorage.setItem("tsiStudioRawEmailThread", trimmedThread);
    try {
      const parsedSession = await parseEmailThread(trimmedThread);
      sessionStorage.setItem("tsiStudioSessionId", parsedSession.sessionId);
      sessionStorage.setItem("tsiStudioSession", JSON.stringify(parsedSession));
      navigate("/workspace");
    } catch (err) {
      try {
        const localSession = createLocalSession(trimmedThread);
        sessionStorage.setItem("tsiStudioSessionId", localSession.sessionId);
        sessionStorage.setItem("tsiStudioSession", JSON.stringify(localSession));
        navigate("/workspace");
      } catch {
        setError(err.message || "Unable to parse email thread.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleDemo() {
    setEmailThread(demoThread);
    setError("");
  }

  return (
    <div className="landing-page">
      <aside className="landing-sidebar">
        <div>
          <div className="landing-logo">
            <div className="landing-logo-mark" aria-hidden="true">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span>tsi</span>
          </div>

          <nav className="landing-nav">
            <button className="landing-nav-item active">
              <MessageSquare size={22} />
              <span>Studio</span>
            </button>
          </nav>
        </div>

        <div className="landing-sidebar-bottom">
          <div className="landing-user-card">
            <div className="landing-avatar">
              <UserCircle size={34} />
            </div>
            <div>
              <h4>Agent User</h4>
              <p>agent@tsi.com</p>
            </div>
            <ChevronDown size={18} />
          </div>

          <div className="landing-bottom-menu">
            <button>
              <Settings size={19} />
              Settings
            </button>
            <button>
              <LogOut size={19} />
              Log out
            </button>
          </div>
        </div>
      </aside>

      <main className="landing-main">
        <header className="landing-topbar">
          <button className="demo-btn" type="button" onClick={handleDemo}>
            <BookOpen size={18} />
            Demo
          </button>
          <Bell size={26} />
          <HelpCircle size={27} />
        </header>

        <section className="landing-hero">
          <div className="landing-title">
            <h1>Welcome to TSI Studio</h1>
            <p>
              TSI Studio helps support agents analyze customer email threads,
              understand the issue, and draft professional replies in seconds.
            </p>
          </div>

          <div className="hero-illustration" aria-hidden="true">
            <div className="browser-card">
              <div className="browser-top">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <div className="browser-body">
                <div className="mail-icon">
                  <Mail size={32} />
                </div>
                <div className="line short"></div>
                <div className="line medium"></div>
                <div className="line long"></div>
                <div className="line medium"></div>
              </div>
            </div>

            <div className="task-card">
              <div className="task-row">
                <span>
                  <Check size={13} />
                </span>
                <div></div>
              </div>
              <div className="task-row">
                <span>
                  <Check size={13} />
                </span>
                <div></div>
              </div>
            </div>

            <Sparkles className="sparkle" size={54} />
          </div>
        </section>

        <form
          className="thread-card"
          aria-label="Email thread input"
          aria-busy={isSubmitting}
          onSubmit={handleEmailSubmit}
        >
          <h2>Your Email Thread</h2>
          <div className="thread-input-row">
            <textarea
              placeholder="Paste the full customer email thread here..."
              value={emailThread}
              onChange={(event) => setEmailThread(event.target.value)}
              disabled={isSubmitting}
            />
            <button type="submit" aria-label="Send email thread" disabled={isSubmitting}>
              {isSubmitting ? <LoadingSpinner label="Parsing email thread" /> : <SendHorizontal size={29} />}
            </button>
          </div>
        </form>
        {error && <p className="landing-error">{error}</p>}

        <section className="landing-card features-card">
          <h2>What TSI Studio can do</h2>
          <div className="features-grid">
            {features.map((item) => (
              <div className="feature-item" key={item.title}>
                <div className="feature-icon">{item.icon}</div>
                <div>
                  <h3>{item.title}</h3>
                  <p>{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
