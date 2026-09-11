const POLL_MINUTES = 2;

// --- Dynamic icon rendering ---

function drawIcon(text, bgColor, fgColor) {
  const size = 128;
  const canvas = new OffscreenCanvas(size, size);
  const ctx = canvas.getContext("2d");

  // Circle background
  ctx.beginPath();
  ctx.arc(size / 2, size / 2, size / 2 - 1, 0, Math.PI * 2);
  ctx.fillStyle = bgColor;
  ctx.fill();

  // Text
  ctx.fillStyle = fgColor;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  let fontSize;
  if (text.length === 1) fontSize = 80;
  else if (text.length === 2) fontSize = 64;
  else fontSize = 48;

  ctx.font = `bold ${fontSize}px Arial, sans-serif`;
  ctx.fillText(text, size / 2, size / 2 + 2);

  return ctx.getImageData(0, 0, size, size);
}

function setIcon(text, bgColor, fgColor) {
  const imageData = drawIcon(text, bgColor, fgColor);
  chrome.action.setIcon({ imageData: { 128: imageData } });
  // Clear badge since icon itself shows the number
  chrome.action.setBadgeText({ text: "" });
}

function updateIcon(pct) {
  let bg, fg;
  if (pct < 0) {
    setIcon("?", "#666", "#ddd");
    return;
  }
  if (pct < 80) { bg = "#D97757"; fg = "#fff"; }
  else { bg = "#E84E4E"; fg = "#fff"; }
  setIcon(String(pct), bg, fg);
}

// --- API ---

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

async function getOrgId() {
  // Org currently selected in claude.ai (matters for accounts with several orgs)
  try {
    const c = await chrome.cookies.get({ url: "https://claude.ai", name: "lastActiveOrg" });
    if (c && UUID_RE.test(c.value)) return c.value;
  } catch { /* fall through */ }

  const data = await chrome.storage.local.get("orgId");
  if (data.orgId) return data.orgId;

  const resp = await fetch("https://claude.ai/api/organizations", {
    headers: { "Accept": "application/json" },
    credentials: "include"
  });
  if (resp.ok) {
    const orgs = await resp.json();
    if (Array.isArray(orgs) && orgs.length > 0) {
      // Prefer a claude.ai (chat) org over API-only orgs
      const chat = orgs.find(o => Array.isArray(o.capabilities) && o.capabilities.includes("chat"));
      const orgId = (chat || orgs[0]).uuid;
      await chrome.storage.local.set({ orgId });
      return orgId;
    }
  }
  return null;
}

async function fetchUsage() {
  // Check if logged in
  let sk;
  try {
    const cookie = await chrome.cookies.get({ url: "https://claude.ai", name: "sessionKey" });
    sk = cookie ? cookie.value : null;
  } catch { sk = null; }

  if (!sk) {
    updateIcon(-1);
    chrome.action.setTitle({ title: "Claude Meter: Not logged in" });
    await chrome.storage.local.set({ status: "Not logged in to claude.ai" });
    return;
  }

  const orgId = await getOrgId();
  if (!orgId) {
    updateIcon(-1);
    chrome.action.setTitle({ title: "Claude Meter: No organization found" });
    await chrome.storage.local.set({ status: "Could not get organization" });
    return;
  }

  try {
    const resp = await fetch(`https://claude.ai/api/organizations/${orgId}/usage`, {
      headers: { "Accept": "application/json" },
      credentials: "include"
    });

    if (resp.status === 429) {
      updateIcon(100);
      chrome.action.setTitle({ title: "Claude: 100% used (rate limited)" });
      await chrome.storage.local.set({ status: "connected", pct5: 100, pct7: null, resetsIn: "Rate limited" });
      return;
    }

    if (resp.status === 401 || resp.status === 403) {
      await chrome.storage.local.remove("orgId");
      updateIcon(-1);
      chrome.action.setTitle({ title: "Claude Meter: Session expired" });
      await chrome.storage.local.set({ status: "Session expired - refresh claude.ai" });
      return;
    }

    if (resp.ok) {
      const data = await resp.json();
      const five = data.five_hour;
      const seven = data.seven_day;

      if (five && "utilization" in five) {
        const pct5 = Math.round(five.utilization);
        const pct7 = seven ? Math.round(seven.utilization) : null;

        updateIcon(pct5);

        // Reset countdown
        let resetsIn = null;
        if (five.resets_at) {
          const secs = Math.floor((new Date(five.resets_at) - new Date()) / 1000);
          if (secs > 0) {
            const h = Math.floor(secs / 3600);
            const m = Math.floor((secs % 3600) / 60);
            resetsIn = h > 0 ? `${h}h${String(m).padStart(2, "0")}m` : `${m}m`;
          } else {
            resetsIn = "Resetting...";
          }
        }

        let title = `Claude use: (5h: ${pct5}%`;
        if (pct7 !== null) title += `, 7d: ${pct7}%`;
        if (resetsIn) title += ` | Resets in ${resetsIn}`;
        title += ")";
        chrome.action.setTitle({ title });

        await chrome.storage.local.set({ pct5, pct7, resetsIn, status: "connected" });
        return;
      }
    }

    updateIcon(-1);
    await chrome.storage.local.set({ status: `API: ${resp.status}` });
  } catch (e) {
    updateIcon(-1);
    await chrome.storage.local.set({ status: `Error: ${e.message}` });
  }
}

// --- Tray app connector ---
// Sends sessionKey to Claude Meter tray app on localhost:27182

async function sendKeyToTrayApp() {
  try {
    const cookie = await chrome.cookies.get({ url: "https://claude.ai", name: "sessionKey" });
    if (cookie && cookie.value) {
      let org = null;
      try { org = await getOrgId(); } catch { /* tray app finds it itself */ }
      await fetch("http://127.0.0.1:27182/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sk: cookie.value, org })
      });
    }
  } catch (e) {
    // Tray app not running, ignore
  }
}

// --- Scheduling ---

chrome.alarms.create("poll", { periodInMinutes: POLL_MINUTES });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "poll") {
    fetchUsage();
    sendKeyToTrayApp();
  }
});

chrome.cookies.onChanged.addListener((info) => {
  if (!info.cookie.domain.includes("claude.ai")) return;
  if (info.cookie.name === "sessionKey" || info.cookie.name === "lastActiveOrg") {
    setTimeout(fetchUsage, 2000);
    if (!info.removed) sendKeyToTrayApp();
  }
});

chrome.runtime.onMessage.addListener((msg) => {
  if (msg.action === "refresh") {
    fetchUsage();
    sendKeyToTrayApp();
  }
});

// Initial
fetchUsage();
sendKeyToTrayApp();
