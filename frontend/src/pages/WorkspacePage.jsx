import React from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Bell,
  ChevronDown,
  Copy,
  Edit3,
  LogOut,
  Mail,
  MessageSquare,
  Plus,
  RefreshCw,
  Settings,
  Sparkles,
  UserCircle,
  X,
} from "lucide-react";
import {
  addEmail,
  generateReply,
  getSession,
  regenerateReply,
  resetSession,
} from "../api/client";
import LoadingSpinner from "../components/LoadingSpinner";
import { mergeLocalEmail } from "../utils/localEmailTools";
import "../styles/WorkspacePage.css";

const categories = [
  "Billing Issue",
  "Payment Arrangement",
  "Move / Transfer Service",
  "Name Change",
  "Meter Reading / High Usage",
  "Tenant / Responsibility Transfer",
  "General Inquiry",
  "Verification Needed",
];

const promptTemplates = {
  "Billing Issue": `The customer is asking about a bill, balance, or charges.

Write a response that:
- Thanks the customer.
- Explains the bill clearly.
- Breaks down charges if charge details are provided.
- Mentions previous balance, current charges, budget billing, true-up, late fee, or adjustment only if provided.
- Shows empathy if the customer says they cannot afford the bill.
- Invites additional questions.`,
  "Payment Arrangement": `The customer wants a payment arrangement.

Write a response that:
- Thanks the customer.
- Confirms that we can assist with a payment arrangement if account access is verified.
- If the customer is not verified, request the missing verification.
- If balance is provided, ask when they can pay that balance.
- Do not promise approval unless backend/account data confirms eligibility.
- Keep the response supportive and professional.`,
  "Move / Transfer Service": `The customer wants to transfer or start service at a new address.

Write a response that:
- Thanks the customer.
- Confirms the new service address if available.
- Requests connection and disconnection dates if missing.
- Explains that a new account number may be created.
- Mentions current price plan transfer only when supported by backend/account data.
- Mentions connection fee or loyalty credit only if provided by backend/account data.
- Gives clear next steps.`,
  "Name Change": `The customer is requesting a name change on the account.

Write a formal Georgia Natural Gas customer care response that:

- Thanks the customer for contacting Georgia Natural Gas.
- Includes appreciation language.
- Politely requests the first and last name needed for the change.
- Politely requests the reason for the name change.
- Requests the effective date only if it was not already provided by the customer.
- Acknowledges any effective date already provided.
- Uses professional customer-service wording similar to utility company email correspondence.
- Includes a professional support closing paragraph.
- Ends with:
  "Please let us know if you have any additional questions or concerns."

Use this template as the starting point:

Dear {customer_name},

Thank you for contacting Georgia Natural Gas. We appreciate the opportunity to assist you.

Please provide us with the first and last name and the reason for the name change. Please let us know if you have any additional questions or concerns. We hope you have a great day.

We value your business and look forward to continuing to meet your natural gas needs. If you have any questions or require additional information, please reply to this email or contact our Customer Care Center at 770.850.6200 (inside metro Atlanta) or 1.877.850.6200 (outside metro Atlanta) Monday through Friday from 7 a.m. until 8 p.m. and Saturdays from 8 a.m. until 5 p.m.

Sincerely,

Customer Care Team
Georgia Natural Gas

Do not add conditional wording such as "if different from" when the customer has already provided a date.
Do not confirm the name change has been completed unless backend confirms it.`,
  "Meter Reading / High Usage": `The customer is disputing high usage or meter readings.

METER READING / HIGH USAGE RESPONSE RULES:

- This category uses an approved GNG template. The final response must stay very close to the approved template text.
- If the email contains an account number and customer details, assume the account has already been reviewed internally.
- Respond confidently and professionally using the approved GNG meter-analysis wording.
- Avoid asking for additional verification unless the thread specifically indicates verification is missing.
- For meter check, high usage, or incorrect-reading disputes, use the approved template below as the default response pattern unless agent instructions or backend data provide a different investigation result.
- State that a meter reading analysis was completed and that the meter readings show within the accepted threshold limits unless backend data or agent instructions explicitly say otherwise.
- Include billing in arrears and winter usage wording when the disputed months include winter or cold-weather months.
- Maintain a reassuring and professional tone.
- Do not use uncertain language such as:
  "we do not have access"
  "we cannot confirm"
  "please provide verification"
  unless explicitly required by the thread.
- Do not add extra advice about visual inspection, external factors, or further channels unless agent instructions require it.
- Do not over-explain historical usage or heating demand beyond the approved template language.
- Keep the response close to the approved GNG wording and avoid making it longer than necessary.
- Do not rewrite this into a generic customer-service explanation.
- Do not replace "Thank you for choosing Georgia Natural Gas" with "Thank you for contacting Georgia Natural Gas."
- Do not replace "We did a meter reading analysis of your meter" with softer language such as "we reviewed the information provided."

Approved default template:

Dear {customer_name},

Thank you for choosing Georgia Natural Gas. I appreciate the opportunity to assist you with your account. We did a meter reading analysis of your meter and the meter readings show within the accepted threshold limits. Please keep in mind that we bill in arrears and are still billing for winter usage. Please let us know if you have any additional questions or concerns. We hope you have a great day.

We value your business and look forward to continuing to meet your natural gas needs. If you have any questions or require additional information, please reply to this email or contact our Customer Care Center at 770.850.6200 (inside metro Atlanta) or 1.877.850.6200 (outside metro Atlanta) Monday through Friday from 7a.m. until 8 p.m. and Saturdays from 8 a.m. until 5 p.m.

Sincerely,

Customer Care Team
Georgia Natural Gas`,
  "Tenant / Responsibility Transfer": `The customer is asking whether a tenant can pay or take over service.

Write a response that:
- Explains that the tenant must apply for service in their own name.
- Explains they can call or apply online if allowed.
- Explains that once tenant service starts, the owner's account may close.
- Offers to process a stop-service request if the customer wants service removed from their name.`,
  "General Inquiry": `The customer has a general Georgia Natural Gas service question.

Write a response that:
- Thanks the customer.
- Answers only with confirmed information from the email thread, agent instructions, or backend account data.
- If account-specific information is required, request the minimum missing verification.
- Gives clear next steps.
- Keeps the message formal, polished, customer-service oriented, and similar to official Georgia Natural Gas email correspondence.
- Includes standard customer support closing language when appropriate.
- Responses should generally be 2-4 professional paragraphs for customer service requests.`,
  "Verification Needed": `The customer request requires account verification before account-specific help can continue.

Write a response that:
- Thanks the customer.
- Requests only the missing verification details.
- Does not ask for details the customer already provided in the thread.
- Does not discuss balances, charges, service dates, fees, credits, or account changes unless backend data confirms them.
- Keeps the request formal, professional, and similar to official Georgia Natural Gas email correspondence.
- Includes standard customer support closing language when appropriate.`,
};

export default function WorkspacePage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [sessionId, setSessionId] = React.useState("");
  const [emails, setEmails] = React.useState([]);
  const [detectedCategory, setDetectedCategory] = React.useState("");
  const [selectedCategory, setSelectedCategory] = React.useState("General Inquiry");
  const [promptText, setPromptText] = React.useState(promptTemplates["General Inquiry"]);
  const [reply, setReply] = React.useState("");
  const [isEditing, setIsEditing] = React.useState(false);
  const [expandedEmails, setExpandedEmails] = React.useState(() => new Set());
  const [isLoading, setIsLoading] = React.useState(true);
  const [isAddEmailOpen, setIsAddEmailOpen] = React.useState(false);
  const [isPromptModalOpen, setIsPromptModalOpen] = React.useState(false);
  const [newEmailContent, setNewEmailContent] = React.useState("");
  const [draftPromptText, setDraftPromptText] = React.useState("");
  const [isAddingEmail, setIsAddingEmail] = React.useState(false);
  const [isGenerating, setIsGenerating] = React.useState(false);
  const [generationAction, setGenerationAction] = React.useState("");
  const [isResetting, setIsResetting] = React.useState(false);
  const [statusMessage, setStatusMessage] = React.useState("");
  const [statusType, setStatusType] = React.useState("info");

  React.useEffect(() => {
    const id = searchParams.get("sessionId") || sessionStorage.getItem("tsiStudioSessionId");
    if (!id) {
      navigate("/");
      return;
    }

    setSessionId(id);
    loadSession(id);
  }, [navigate, searchParams]);

  async function loadSession(id) {
    setIsLoading(true);
    showStatus("");
    try {
      const session = await getSession(id);
      applySession(session);
    } catch (error) {
      const cached = sessionStorage.getItem("tsiStudioSession");
      if (cached) {
        applySession(JSON.parse(cached));
      } else {
        showStatus(error.message || "Unable to load session.", "error");
      }
    } finally {
      setIsLoading(false);
    }
  }

  function showStatus(message, type = "info") {
    setStatusMessage(message);
    setStatusType(type);
  }

  function applySession(session) {
    const category = normalizeCategory(
      session.selectedCategory || session.detectedCategory || "General Inquiry"
    );
    const nextPrompt = session.prompt || promptTemplates[category];

    setSessionId(session.sessionId);
    setEmails(session.emails || []);
    setDetectedCategory(session.detectedCategory || "");
    setSelectedCategory(category);
    setPromptText(nextPrompt);
    setReply(session.generatedReply || "");
    setExpandedEmails(new Set());
    sessionStorage.setItem("tsiStudioSessionId", session.sessionId);
    sessionStorage.setItem("tsiStudioSession", JSON.stringify(session));
  }

  function updateCachedSession(changes) {
    const cached = sessionStorage.getItem("tsiStudioSession");
    const currentSession = cached ? JSON.parse(cached) : {};
    sessionStorage.setItem(
      "tsiStudioSession",
      JSON.stringify({
        ...currentSession,
        sessionId,
        emails,
        detectedCategory,
        selectedCategory,
        prompt: promptText,
        generatedReply: reply,
        ...changes,
      })
    );
  }

  function normalizeCategory(category) {
    return categories.includes(category) ? category : "General Inquiry";
  }

  function handleCategoryChange(event) {
    const nextCategory = normalizeCategory(event.target.value);
    const nextPrompt = promptTemplates[nextCategory];
    setSelectedCategory(nextCategory);
    setPromptText(nextPrompt);
    updateCachedSession({ selectedCategory: nextCategory, prompt: nextPrompt });
  }

  function toggleEmail(position) {
    setExpandedEmails((current) => {
      const next = new Set(current);
      if (next.has(position)) {
        next.delete(position);
      } else {
        next.add(position);
      }
      return next;
    });
  }

  function openAddEmailModal() {
    setNewEmailContent("");
    setIsAddEmailOpen(true);
    showStatus("");
  }

  function closeAddEmailModal() {
    if (isAddingEmail) return;
    setIsAddEmailOpen(false);
    setNewEmailContent("");
  }

  function openPromptModal() {
    setDraftPromptText(promptText);
    setIsPromptModalOpen(true);
    showStatus("");
  }

  function closePromptModal() {
    setIsPromptModalOpen(false);
    setDraftPromptText("");
  }

  function handlePromptSave(event) {
    event.preventDefault();
    const nextPrompt = draftPromptText.trim();
    if (!nextPrompt) {
      showStatus("Prompt cannot be empty.", "error");
      return;
    }
    setPromptText(nextPrompt);
    updateCachedSession({ prompt: nextPrompt });
    setIsPromptModalOpen(false);
    setDraftPromptText("");
    showStatus("Prompt updated.");
  }

  async function handleAddEmailSubmit(event) {
    event.preventDefault();
    const emailContent = newEmailContent.trim();
    if (!emailContent) {
      showStatus("Paste the new email content before adding.", "error");
      return;
    }

    setIsAddingEmail(true);
    showStatus("Adding email...");
    try {
      const updated = await addEmail(sessionId, emailContent);
      const category = normalizeCategory(updated.selectedCategory || updated.detectedCategory || selectedCategory);
      setEmails(updated.emails);
      setDetectedCategory(updated.detectedCategory || detectedCategory);
      setSelectedCategory(category);
      updateCachedSession({
        emails: updated.emails,
        detectedCategory: updated.detectedCategory,
        selectedCategory: category,
      });
      setNewEmailContent("");
      setIsAddEmailOpen(false);
      showStatus("Email history updated.");
    } catch (error) {
      const cached = sessionStorage.getItem("tsiStudioSession");
      if (!cached) {
        showStatus(error.message || "Unable to add email.", "error");
      } else {
        const localSession = mergeLocalEmail(JSON.parse(cached), emailContent);
        setEmails(localSession.emails);
        setDetectedCategory(localSession.detectedCategory || detectedCategory);
        setSelectedCategory(normalizeCategory(localSession.selectedCategory || localSession.detectedCategory));
        sessionStorage.setItem("tsiStudioSession", JSON.stringify(localSession));
        setNewEmailContent("");
        setIsAddEmailOpen(false);
        showStatus("Email history updated locally.");
      }
    } finally {
      setIsAddingEmail(false);
    }
  }

  async function handleGenerate() {
    if (!sessionId) return;
    setIsGenerating(true);
    setGenerationAction("generate");
    showStatus("Generating reply...");
    try {
      const result = await generateReply(sessionId, {
        selectedCategory,
        agentInstructions: promptText,
        accountData: {},
      });
      setReply(result.reply);
      setIsEditing(false);
      updateCachedSession({
        selectedCategory,
        prompt: promptText,
        generatedReply: result.reply,
      });
      showStatus("Reply generated.");
    } catch (error) {
      showStatus(error.message || "Unable to generate reply.", "error");
    } finally {
      setIsGenerating(false);
      setGenerationAction("");
    }
  }

  async function handleRegenerate() {
    if (!sessionId) return;
    setIsGenerating(true);
    setGenerationAction("regenerate");
    showStatus("Regenerating reply...");
    try {
      const result = await regenerateReply(sessionId, {
        selectedCategory,
        agentInstructions: promptText,
        previousReply: reply,
      });
      setReply(result.reply);
      setIsEditing(false);
      updateCachedSession({
        selectedCategory,
        prompt: promptText,
        generatedReply: result.reply,
      });
      showStatus("Reply regenerated.");
    } catch (error) {
      showStatus(error.message || "Unable to regenerate reply.", "error");
    } finally {
      setIsGenerating(false);
      setGenerationAction("");
    }
  }

  async function handleCopy() {
    if (!reply.trim()) return;
    try {
      await navigator.clipboard.writeText(reply);
      showStatus("Reply copied to clipboard.");
    } catch {
      showStatus("Unable to copy reply to clipboard.", "error");
    }
  }

  async function handleNewChat() {
    setIsResetting(true);
    if (sessionId && !sessionId.startsWith("local-")) {
      try {
        await resetSession(sessionId);
      } catch {
        // Reset is best-effort; local state still clears.
      }
    }
    sessionStorage.removeItem("tsiStudioSessionId");
    sessionStorage.removeItem("tsiStudioSession");
    sessionStorage.removeItem("tsiStudioRawEmailThread");
    setSessionId("");
    setEmails([]);
    setDetectedCategory("");
    setSelectedCategory("General Inquiry");
    setPromptText(promptTemplates["General Inquiry"]);
    setReply("");
    setIsEditing(false);
    setNewEmailContent("");
    setIsAddEmailOpen(false);
    setIsResetting(false);
    navigate("/");
  }

  return (
    <div className="workspace-page">
      <aside className="workspace-sidebar">
        <div>
          <div className="workspace-logo">
            <div className="workspace-logo-mark" aria-hidden="true">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span>tsi</span>
          </div>

          <nav className="workspace-nav">
            <button className="workspace-nav-item active">
              <MessageSquare size={15} />
              <span>Studio</span>
            </button>
          </nav>
        </div>

        <div className="workspace-sidebar-bottom">
          <div className="workspace-user-card">
            <div className="workspace-avatar">
              <UserCircle size={25} />
            </div>
            <div>
              <h4>Agent User</h4>
              <p>agent@tsi.com</p>
            </div>
            <ChevronDown size={14} />
          </div>

          <div className="workspace-bottom-menu">
            <button>
              <Settings size={15} />
              Settings
            </button>
            <button>
              <LogOut size={15} />
              Log out
            </button>
          </div>
        </div>
      </aside>

      <main className="workspace-main">
        <header className="workspace-topbar">
          <button className="new-chat-btn" onClick={handleNewChat} disabled={isResetting}>
            {isResetting ? <LoadingSpinner label="Starting new chat" /> : <Plus size={17} />}
            {isResetting ? "Resetting" : "New Chat"}
          </button>
          <Bell size={21} />
          <div className="workspace-initials">AU</div>
          <ChevronDown size={16} />
        </header>

        <div className="workspace-content">
          <section className="history-panel">
            <div className="panel-heading">
              <div>
                <h2>Customer Email History</h2>
                <p>All emails in this thread, sorted from oldest to newest.</p>
              </div>
              <button onClick={openAddEmailModal} disabled={isLoading || isAddingEmail}>
                {isAddingEmail ? <LoadingSpinner label="Adding email" /> : <Plus size={15} />}
                Add Email
              </button>
            </div>

            <div className="email-timeline">
              {isLoading && (
                <p className="status-message">
                  <LoadingSpinner label="Loading email history" />
                  Loading email history...
                </p>
              )}
              {!isLoading &&
                emails.map((email) => {
                  const position = email.position || email.id;
                  const expanded = expandedEmails.has(position);
                  return (
                    <article className={`email-card ${expanded ? "expanded" : ""}`} key={position}>
                      <div className="timeline-dot"></div>
                      <div className="email-icon">
                        <Mail size={18} />
                      </div>
                      <button
                        className="email-toggle"
                        type="button"
                        onClick={() => toggleEmail(position)}
                        aria-expanded={expanded}
                      >
                        <div className="email-meta">
                          <h3>
                            {position}. {email.type}
                          </h3>
                          <span>{email.sender}</span>
                          <time>{email.timestamp || email.date}</time>
                        </div>
                        <p>{expanded ? email.body : email.preview || email.body}</p>
                        {expanded && (
                          <dl className="email-details">
                            <div>
                              <dt>From</dt>
                              <dd>{email.fromName || email.sender}</dd>
                            </div>
                            <div>
                              <dt>Subject</dt>
                              <dd>{email.subject || "No subject"}</dd>
                            </div>
                          </dl>
                        )}
                      </button>
                    </article>
                  );
                })}
            </div>
          </section>

          <section className="workspace-right">
            <article className="prompt-panel">
              <div className="panel-heading">
                <div>
                  <h2>Enter / Edit Prompt</h2>
                  <p>Provide instructions for how you want the AI to analyze and draft the reply.</p>
                </div>
                <button className="primary-outline" onClick={handleGenerate} disabled={isGenerating || isLoading}>
                  {generationAction === "generate" ? (
                    <LoadingSpinner label="Generating reply" />
                  ) : (
                    <Sparkles size={16} />
                  )}
                  {generationAction === "generate" ? "Generating" : "Apply & Regenerate"}
                </button>
              </div>

              <div className="category-row">
                <label htmlFor="category">Category</label>
                <div className="select-wrap">
                  <select id="category" value={selectedCategory} onChange={handleCategoryChange}>
                    {categories.map((category) => (
                      <option value={category} key={category}>
                        {category}
                      </option>
                    ))}
                  </select>
                  <ChevronDown size={16} />
                </div>
                {detectedCategory && detectedCategory !== selectedCategory && (
                  <span className="detected-pill">Detected: {detectedCategory}</span>
                )}
              </div>

              <div className="prompt-box">
                <textarea
                  className="prompt-textarea"
                  value={promptText}
                  maxLength={4000}
                  readOnly
                />
              </div>

              <div className="prompt-footer">
                <span>{promptText.length} / 4000</span>
                <button type="button" onClick={openPromptModal}>
                  Edit Prompt
                </button>
              </div>
            </article>

            <article className="reply-panel">
              <div className="panel-heading">
                <div>
                  <h2>Clean & Detailed Reply</h2>
                  <p>AI-generated reply based on the prompt and email thread. You can edit before sending.</p>
                </div>
                <div className="reply-actions">
                  <button onClick={handleRegenerate} disabled={isGenerating || !reply}>
                    {generationAction === "regenerate" ? (
                      <LoadingSpinner label="Regenerating reply" />
                    ) : (
                      <RefreshCw size={16} />
                    )}
                    {generationAction === "regenerate" ? "Regenerating" : "Regenerate"}
                  </button>
                  <button className="icon-only" onClick={handleCopy} disabled={!reply} aria-label="Copy reply">
                    <Copy size={15} />
                  </button>
                </div>
              </div>

              <textarea
                className="reply-textarea"
                value={reply}
                readOnly={!isEditing}
                onChange={(event) => {
                  const nextReply = event.target.value;
                  setReply(nextReply);
                  updateCachedSession({ generatedReply: nextReply });
                }}
                placeholder="Click Apply & Regenerate to generate a customer-ready reply."
              />

              <div className="reply-footer">
                <button
                  className="secondary-action"
                  onClick={() => setIsEditing((current) => !current)}
                  disabled={!reply}
                >
                  <Edit3 size={16} />
                  {isEditing ? "Editing Draft" : "Edit Draft"}
                </button>
                <button className="primary-action" onClick={handleCopy} disabled={!reply}>
                  <Copy size={17} />
                  Copy to Clipboard
                </button>
              </div>
            </article>

            {statusMessage && (
              <p className={`workspace-status ${statusType === "error" ? "error" : ""}`}>
                {statusMessage}
              </p>
            )}
          </section>
        </div>
      </main>

      {isAddEmailOpen && (
        <div className="modal-backdrop" role="presentation" onMouseDown={closeAddEmailModal}>
          <form
            className="add-email-modal"
            aria-label="Add email"
            onSubmit={handleAddEmailSubmit}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="modal-heading">
              <div>
                <h2>Add Email</h2>
                <p>Paste the new customer email to update this thread.</p>
              </div>
              <button type="button" className="modal-close" onClick={closeAddEmailModal}>
                <X size={18} />
              </button>
            </div>

            <textarea
              className="add-email-textarea"
              value={newEmailContent}
              onChange={(event) => setNewEmailContent(event.target.value)}
              placeholder="Paste new email content here..."
              autoFocus
            />

            <div className="modal-actions">
              <button type="button" className="secondary-action" onClick={closeAddEmailModal}>
                Cancel
              </button>
              <button
                type="submit"
                className="primary-action"
                disabled={isAddingEmail || !newEmailContent.trim()}
              >
                {isAddingEmail && <LoadingSpinner label="Adding email" />}
                {isAddingEmail ? "Adding" : "Add Email"}
              </button>
            </div>
          </form>
        </div>
      )}

      {isPromptModalOpen && (
        <div className="modal-backdrop" role="presentation" onMouseDown={closePromptModal}>
          <form
            className="edit-prompt-modal"
            aria-label="Edit prompt"
            onSubmit={handlePromptSave}
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="modal-heading">
              <div>
                <h2>Edit Prompt</h2>
                <p>Adjust the instructions used to generate the customer reply.</p>
              </div>
              <button type="button" className="modal-close" onClick={closePromptModal}>
                <X size={18} />
              </button>
            </div>

            <textarea
              className="edit-prompt-textarea"
              value={draftPromptText}
              maxLength={4000}
              onChange={(event) => setDraftPromptText(event.target.value)}
              autoFocus
            />

            <div className="prompt-modal-footer">
              <span>{draftPromptText.length} / 4000</span>
              <div className="modal-actions-inline">
                <button type="button" className="secondary-action" onClick={closePromptModal}>
                  Cancel
                </button>
                <button type="submit" className="primary-action" disabled={!draftPromptText.trim()}>
                  Save Prompt
                </button>
              </div>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
