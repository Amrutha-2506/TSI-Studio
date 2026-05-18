const categoryKeywords = {
  "Billing Issue": [
    "bill",
    "billing",
    "balance",
    "charge",
    "amount",
    "why is my bill",
    "due date",
    "budget billing",
    "true-up",
    "true up",
  ],
  "Payment Arrangement": [
    "payment arrangement",
    "extension",
    "cannot pay",
    "can't pay",
    "pay later",
    "payment plan",
  ],
  "Move / Transfer Service": [
    "new address",
    "moving",
    "transfer service",
    "start service",
    "stop service",
    "close old account",
  ],
  "Name Change": ["name change", "change account name", "update name"],
  "Meter Reading / High Usage": [
    "meter",
    "reading",
    "usage",
    "therms",
    "incorrect reading",
    "high usage",
  ],
  "Tenant / Responsibility Transfer": [
    "tenant",
    "renter",
    "renting my home",
    "pay the fees",
    "service in their name",
  ],
  "Verification Needed": [
    "verify",
    "verification",
    "account number",
    "name on the account",
    "service address",
  ],
};

export function createLocalSession(rawThread) {
  const emails = parseLocalEmailThread(rawThread);
  const detectedCategory = detectLocalCategory(rawThread, emails);
  return {
    sessionId: `local-${Date.now()}`,
    rawEmailThread: rawThread,
    emails,
    detectedCategory,
    selectedCategory: detectedCategory,
    prompt: "",
    generatedReply: "",
    isLocalOnly: true,
  };
}

export function mergeLocalEmail(session, emailContent) {
  const rawEmailThread = `${session.rawEmailThread || ""}\n\n---\n\n${emailContent}`.trim();
  const emails = parseLocalEmailThread(rawEmailThread);
  const detectedCategory = detectLocalCategory(rawEmailThread, emails);
  return {
    ...session,
    rawEmailThread,
    emails,
    detectedCategory,
    selectedCategory: session.selectedCategory || detectedCategory,
  };
}

export function parseLocalEmailThread(rawThread) {
  const text = cleanText(rawThread);
  const chunks = splitThread(text);
  const parsed = chunks
    .map((chunk, index) => parseChunk(chunk, index))
    .filter((email) => email.body.length > 0);

  const emails = sortLocalEmails(parsed.length ? parsed : [parseChunk(text, 0)]);

  return emails.map((email, index) => {
    const position = index + 1;
    return {
      id: position,
      position,
      type: emailType(position),
      sender: senderLabel(email.senderType),
      senderType: email.senderType,
      from: email.from || email.fromName || senderLabel(email.senderType),
      fromName: email.fromName || senderLabel(email.senderType),
      to: email.to,
      subject: email.subject,
      date: email.date,
      timestamp: email.date || "Unknown",
      preview: makePreview(email.body),
      body: email.body,
      hasServiceAddress: /\b\d{2,6}\s+[A-Za-z0-9 .'-]+/.test(email.body),
    };
  });
}

export function detectLocalCategory(rawThread, emails = []) {
  const latestCustomer = [...emails]
    .reverse()
    .find((email) => email.senderType === "Customer" || email.sender === "Customer");
  const source = latestCustomer
    ? `${latestCustomer.subject || ""} ${latestCustomer.body || ""}`
    : rawThread;
  const best = bestCategory(source, false);
  if (best) return best;
  return bestCategory(rawThread, true) || "General Inquiry";
}

function splitThread(text) {
  const lines = text.split(/\r?\n/);
  const starts = [];

  lines.forEach((line, index) => {
    if (line.trim().toLowerCase().startsWith("from:") && hasCompleteHeaderBlock(lines, index)) {
      starts.push(index);
    }
  });

  if (starts.length) {
    return starts.map((start, index) => {
      const end = starts[index + 1] ?? lines.length;
      return cleanText(lines.slice(start, end).join("\n"));
    }).filter(Boolean);
  }

  return [text];
}

function parseChunk(chunk) {
  const from = headerValue(chunk, "from");
  const date = headerValue(chunk, "sent") || headerValue(chunk, "date") || "";
  const subject = headerValue(chunk, "subject");
  const to = headerValue(chunk, "to");
  const blockLines = chunk.split(/\r?\n/);
  const subjectIndex = blockLines.findIndex((line) => /^\s*subject\s*:/i.test(line));
  const bodyLines =
    subjectIndex >= 0
      ? blockLines.slice(subjectIndex + 1)
      : blockLines.filter((line) => !/^\s*(from|to|sent|date|subject|cc|bcc)\s*:/i.test(line));
  const body = cleanEmailBody(bodyLines.join("\n"));
  const fromName = cleanName(from);
  const senderType = getSenderType(from);

  return { from, fromName, to, subject, date, body, senderType };
}

function hasCompleteHeaderBlock(lines, startIndex) {
  const labels = new Set();

  for (const [offset, line] of lines.slice(startIndex, startIndex + 12).entries()) {
    const trimmed = line.trim().toLowerCase();
    if (offset > 0 && trimmed.startsWith("from:")) return false;
    if (/^from\s*:/.test(trimmed)) labels.add("from");
    if (/^(sent|date)\s*:/.test(trimmed)) labels.add("sent");
    if (/^to\s*:/.test(trimmed)) labels.add("to");
    if (/^subject\s*:/.test(trimmed)) labels.add("subject");
    if (["from", "sent", "to", "subject"].every((label) => labels.has(label))) return true;
  }

  return false;
}

function getSenderType(fromField = "") {
  const from = fromField.toLowerCase();
  const gngPatterns = [
    "gng customer service",
    "gng customer care",
    "georgia natural gas",
    "customerservice@gng.com",
    "customerservice@gngcs.com",
    "do_not_reply@gng.com",
    "gngemail@response.gng.com",
    "response.gng.com",
    "mail.gng.com",
    "@gng.com",
    "@gngcs.com",
  ];

  return gngPatterns.some((pattern) => from.includes(pattern)) ? "GNG" : "Customer";
}

function headerValue(text, label) {
  const match = text.match(new RegExp(`^\\s*${label}\\s*:\\s*(.+)$`, "im"));
  return match ? match[1].trim() : "";
}

function cleanName(value) {
  return (value || "").replace(/<[^>]+>/g, "").replace(/["']/g, "").trim();
}

function cleanText(value) {
  return (value || "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function cleanEmailBody(body = "") {
  const ignoredPatterns = [
    /Get Outlook for iOS/i,
    /Yahoo Mail: Search, Organize, Conquer/i,
    /VIEW\s*&\s*PAY\s+NOW/i,
    /cid:image[^\s]*/i,
  ];

  return cleanText(
    body
      .split(/\r?\n/)
      .filter((line) => {
        const trimmed = line.trim();
        if (/^(from|to|sent|date|subject|cc|bcc)\s*:/i.test(trimmed)) return false;
        return !ignoredPatterns.some((pattern) => pattern.test(trimmed));
      })
      .join("\n")
  );
}

function makePreview(body) {
  const compact = cleanText(body).replace(/\s+/g, " ");
  return compact.length > 92 ? `${compact.slice(0, 89).trim()}...` : compact;
}

function emailType(position) {
  return position === 1 ? "Initial Email" : "Follow-up Email";
}

function senderLabel(senderType) {
  return senderType === "GNG" ? "From GNG" : "From Customer";
}

function sortLocalEmails(emails) {
  const datedEmails = emails.map((email, index) => ({
    email,
    index,
    timestamp: parseEmailDate(email.date),
  }));
  const hasParsedDates = datedEmails.some((item) => item.timestamp !== null);

  if (!hasParsedDates && emails.length > 1) {
    return [...emails].reverse();
  }

  return datedEmails
    .sort((first, second) => {
      if (first.timestamp !== null && second.timestamp !== null) {
        return first.timestamp - second.timestamp;
      }
      if (first.timestamp !== null) return -1;
      if (second.timestamp !== null) return 1;
      return first.index - second.index;
    })
    .map((item) => item.email);
}

function parseEmailDate(value = "") {
  const normalized = value
    .replace(/^\s*(?:mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?),\s*/i, "")
    .replace(/\s+at\s+/i, " ")
    .replace(/\s+(?:ET|EST|EDT|CT|CST|CDT|PT|PST|PDT)\b/i, "")
    .replace(/\s+/g, " ")
    .trim();

  const explicitTimestamp = parseKnownEmailDate(normalized);
  if (explicitTimestamp !== null) return explicitTimestamp;

  const fallbackTimestamp = Date.parse(normalized);
  return Number.isNaN(fallbackTimestamp) ? null : fallbackTimestamp;
}

function parseKnownEmailDate(value) {
  const monthNames = {
    jan: 0,
    january: 0,
    feb: 1,
    february: 1,
    mar: 2,
    march: 2,
    apr: 3,
    april: 3,
    may: 4,
    jun: 5,
    june: 5,
    jul: 6,
    july: 6,
    aug: 7,
    august: 7,
    sep: 8,
    september: 8,
    oct: 9,
    october: 9,
    nov: 10,
    november: 10,
    dec: 11,
    december: 11,
  };

  const monthFirst = value.match(
    /^([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{4}),?\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)$/i
  );
  if (monthFirst) {
    return buildTimestamp({
      month: monthNames[monthFirst[1].toLowerCase()],
      day: monthFirst[2],
      year: monthFirst[3],
      hour: monthFirst[4],
      minute: monthFirst[5],
      second: monthFirst[6],
      meridiem: monthFirst[7],
    });
  }

  const dayFirst = value.match(
    /^(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4}),?\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)$/i
  );
  if (dayFirst) {
    return buildTimestamp({
      day: dayFirst[1],
      month: monthNames[dayFirst[2].toLowerCase()],
      year: dayFirst[3],
      hour: dayFirst[4],
      minute: dayFirst[5],
      second: dayFirst[6],
      meridiem: dayFirst[7],
    });
  }

  const numeric = value.match(
    /^(\d{1,2})\/(\d{1,2})\/(\d{2,4})\s+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)$/i
  );
  if (numeric) {
    const year = Number(numeric[3]) < 100 ? Number(numeric[3]) + 2000 : Number(numeric[3]);
    return buildTimestamp({
      month: Number(numeric[1]) - 1,
      day: numeric[2],
      year,
      hour: numeric[4],
      minute: numeric[5],
      second: numeric[6],
      meridiem: numeric[7],
    });
  }

  return null;
}

function buildTimestamp({ year, month, day, hour, minute, second = 0, meridiem }) {
  if (month === undefined) return null;
  let hourValue = Number(hour);
  if (meridiem.toUpperCase() === "PM" && hourValue !== 12) hourValue += 12;
  if (meridiem.toUpperCase() === "AM" && hourValue === 12) hourValue = 0;
  return new Date(Number(year), month, Number(day), hourValue, Number(minute), Number(second || 0)).getTime();
}

function bestCategory(text, allowVerification) {
  const source = (text || "").toLowerCase();
  let best = "";
  let bestScore = 0;

  Object.entries(categoryKeywords).forEach(([category, keywords]) => {
    if (!allowVerification && category === "Verification Needed") return;
    const score = keywords.filter((keyword) => source.includes(keyword)).length;
    if (score > bestScore) {
      best = category;
      bestScore = score;
    }
  });

  return bestScore > 0 ? best : "";
}
